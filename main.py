from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, ListItem, ListView, Label, ProgressBar
from textual.containers import Vertical, Horizontal
from textual import work, on
import asyncio
import os
import threading
from pynput import keyboard

from ytm_client import YTMClient
from player import Player

class SongCard(ListItem):
    def __init__(self, song_data):
        super().__init__()
        self.song_data = song_data
        self.title = str(song_data.get('title', 'Canción'))
        self.artist = str(song_data.get('artist', 'Artista'))

    def compose(self) -> ComposeResult:
        with Horizontal(classes="card_wrapper"):
            yield Label("  ", classes="card_icon")
            with Vertical(classes="card_info_col"):
                yield Label(f"[bold]{self.title[:50]}[/bold]", classes="card_title")
                yield Label(self.artist[:45], classes="card_artist")

class YTMApp(App):
    CSS = """
    Screen { background: #0a0a0a; color: #ffffff; }
    #main_container { layout: horizontal; height: 1fr; }
    #sidebar { width: 25; background: #121212; border-right: solid #222222; padding: 1; }
    .sidebar_section { color: #555555; text-style: bold; margin: 1 0 0 1; }
    #content_area { width: 1fr; background: #0a0a0a; }
    #top_bar { height: auto; padding: 1; background: #0d0d0d; border-bottom: solid #222222; }
    #search_input { background: #1a1a1a; border: solid #333333; color: white; }
    SongCard { height: 4; margin-bottom: 1; background: #141414; border: solid #222222; padding: 0; }
    SongCard:focus { background: #1a1a1a; border: solid $accent; }
    .card_wrapper { height: 100%; width: 100%; }
    .card_icon { color: $accent; margin: 1 2; }
    .card_info_col { width: 1fr; height: 100%; align-vertical: middle; }
    #player_bar { height: 6; background: #121212; border-top: solid #333333; padding: 1 2; }
    #now_playing_info { width: 40%; }
    #playback_controls { width: 1fr; content-align: center middle; }
    #song_progress { width: 100%; margin-top: 1; }
    #vol_label { width: 15; text-align: right; color: $accent; }
    """

    BINDINGS = [
        ("space", "toggle_pause", "Play/Pause"),
        ("ctrl+alt+home", "next_song", "Sig"),
        ("ctrl+alt+insert", "prev_song", "Ant"),
        ("ctrl+alt+page_up", "volume_up", "Vol+"),
        ("ctrl+alt+page_down", "volume_down", "Vol-"),
        ("s", "focus_search", "Buscar"),
        ("l", "load_likes", "Likes"),
        ("q", "quit", "Salir"),
    ]

    def __init__(self):
        super().__init__()
        self.client = YTMClient()
        # Escuchamos progreso y cambios de estado (volumen/idle)
        self.player = Player(
            on_progress=self.update_progress, 
            on_status_change=self.handle_external_status
        )
        self.current_volume = 100
        self.queue = []
        self.current_index = -1
        self._is_loading_next = False
        self.hotkey_listener = None

    def start_global_listener(self):
        import signal
        def on_next(): self.call_from_thread(self.action_next_song)
        def on_prev(): self.call_from_thread(self.action_prev_song)
        def on_vol_up(): self.call_from_thread(self.action_volume_up)
        def on_vol_down(): self.call_from_thread(self.action_volume_down)

        # Señales para control externo (Hyprland)
        # Usamos call_next porque las señales se reciben en el hilo principal
        signal.signal(signal.SIGUSR1, lambda sig, frame: self.call_next(self.action_next_song))
        signal.signal(signal.SIGUSR2, lambda sig, frame: self.call_next(self.action_prev_song))

        try:
            self.hotkey_listener = keyboard.GlobalHotKeys({
                '<ctrl>+<alt>+<home>': on_next,
                '<ctrl>+<alt>+<insert>': on_prev,
                '<ctrl>+<alt>+<page_up>': on_vol_up,
                '<ctrl>+<alt>+<page_down>': on_vol_down,
            })
            self.hotkey_listener.start()
        except Exception:
            # En Wayland pynput puede fallar, pero las señales seguirán funcionando
            pass

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main_container"):
            with Vertical(id="sidebar"):
                is_auth = os.path.exists("browser.json")
                user = self.client.ytm.get_account_info().get('accountName', 'Invitado') if is_auth else 'Invitado'
                yield Label(f"󰀉 [bold cyan]{user}[/bold cyan]\n")
                yield Label("MENÚ", classes="sidebar_section")
                with ListView(id="sidebar_nav"):
                    yield ListItem(Label("   Para ti"), id="nav_home")
                    yield ListItem(Label("   Me gusta"), id="nav_likes")
            
            with Vertical(id="content_area"):
                with Vertical(id="top_bar"):
                    yield Input(placeholder="  Buscar música...", id="search_input")
                yield ListView(id="results_list")

        with Horizontal(id="player_bar"):
            with Vertical(id="now_playing_info"):
                yield Label("Nada reproduciendo", id="track_name")
                yield Label("", id="artist_name", classes="card_artist")
            with Vertical(id="playback_controls"):
                yield Label("󰒮  󰐌  󰒭")
                yield ProgressBar(total=100, show_percentage=False, id="song_progress")
            yield Label(f" {self.current_volume}%", id="vol_label")
        yield Footer()

    def update_progress(self, current, duration):
        if duration:
            self.call_from_thread(self.set_progress, (current / duration) * 100)
            # Siguiente canción automática
            if duration - current < 2 and not self._is_loading_next:
                self._is_loading_next = True
                self.call_from_thread(self.action_next_song)

    def set_progress(self, p): self.query_one("#song_progress").progress = p

    def handle_external_status(self, volume, is_idle):
        # Actualizar volumen si cambió externamente
        if int(volume) != self.current_volume:
            self.current_volume = int(volume)
            self.call_from_thread(self.update_vol_label)
        
        # Si MPV entró en idle y no estamos pausados, cargar siguiente
        # Esto permite que 'playerctl next' funcione con nuestra cola
        if is_idle and self.current_index != -1 and not self._is_loading_next:
            self._is_loading_next = True
            self.call_from_thread(self.action_next_song)

    def update_vol_label(self):
        self.query_one("#vol_label").update(f" {self.current_volume}%")

    async def on_mount(self) -> None:
        self.start_global_listener()
        self.load_section("home")

    @work(exclusive=True)
    async def load_section(self, section: str) -> None:
        rl = self.query_one("#results_list", ListView)
        rl.clear()
        songs = []
        try:
            if section == "home":
                songs = await asyncio.to_thread(self.client.get_recommendations)
            elif section == "likes":
                data = await asyncio.to_thread(self.client.ytm.get_liked_songs, 100)
                songs = [{"id": t["videoId"], "title": t["title"], "artist": t["artists"][0]["name"]} for t in data.get("tracks", [])]
        except Exception: pass
        if songs:
            self.queue = songs
            for s in songs: rl.append(SongCard(s))
            rl.focus()

    @on(ListView.Selected)
    def handle_select(self, event: ListView.Selected):
        if event.list_view.id == "sidebar_nav":
            self.load_section("home" if event.item.id == "nav_home" else "likes")
        else:
            self.current_index = self.query_one("#results_list").index
            self.play_current()

    def play_current(self):
        if 0 <= self.current_index < len(self.queue):
            self._is_loading_next = False
            s = self.queue[self.current_index]
            self.query_one("#track_name").update(f"[bold]{s['title']}[/bold]")
            self.query_one("#artist_name").update(s['artist'])
            self.player.play(s['id'])

    def action_next_song(self):
        if self.current_index < len(self.queue) - 1:
            self.current_index += 1
            self.query_one("#results_list").index = self.current_index
            self.play_current()

    def action_prev_song(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.query_one("#results_list").index = self.current_index
            self.play_current()

    def action_toggle_pause(self): self.player.toggle_pause()
    
    def action_volume_up(self):
        self.current_volume = min(100, self.current_volume + 5)
        self.player.set_volume(self.current_volume)
        self.update_vol_label()

    def action_volume_down(self):
        self.current_volume = max(0, self.current_volume - 5)
        self.player.set_volume(self.current_volume)
        self.update_vol_label()

    def action_load_likes(self): self.load_section("likes")
    def action_focus_search(self): self.query_one("#search_input").focus()

    async def on_input_submitted(self, e):
        if e.value: self.do_search(e.value)

    @work(exclusive=True)
    async def do_search(self, q):
        rl = self.query_one("#results_list", ListView)
        rl.clear()
        songs = await asyncio.to_thread(self.client.search_songs, q)
        if songs:
            self.queue = songs
            for s in songs: rl.append(SongCard(s))
            rl.focus()

    def on_unmount(self):
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        self.player.stop()

if __name__ == "__main__":
    YTMApp().run()
