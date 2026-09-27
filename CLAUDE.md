Showtime notes is a project that allows a team to record audio of a performance rehearsal, take notes on what happens during each song, and then when during real performance  they can see their notes for what's about to happen. The backend is Python and utilizes Demucs and Beat_this. The frontend is vuejs typescript. Uses chroma frames to compare the live song with a recorded song to the notes aligned.


# Glossary

Server - the backend python server. there should be one server running for a live show, but there can be many clients
Client - The web browser that connects to a server via web socket. Each client must have a name before connecting
Listener - The client that is streaming audio to the server, typically microphone input, but could also stream media audio. Still behaves like a normal client. There can only be 1 listener per server
Live - refers to the audio currently being received by the server in real-time by the listener.
Show - An ordered collection of songs. There can only be 1 show per server.
Song - The core entity of showtime notes. The song contains audio we recorded, it gets processed, and can be played back, and you can sync live with a song
Buffer - The live audio that the server stores. Normally is just a few seconds, but can be larger if recording.
Recording - Used to create songs. Forces the buffer to preserve audio from moment you start recording. 1 acive recording per server, but can be managed by any client.
Processing - When a recording is finished and saved, it has to be processed, which entails computing the vocal/novocal split and the beats.
Song status - A song could be in the following statuses: recording, finished-recording, processing, ready, syncing.
Syncing - A song is "syncing" while it's the active sync target, whether or not a lock has been acquired yet. Split into two phases (see Phase below).
Phase - Sub-state of syncing: "acquiring" or "tracking".
acquiring (phase) - We're trying to match live with a position in a recorded song, but we haven't acquired a confident lock yet.
tracking (phase) - We have successfully matched live to a specific position of a recorded song. Minor tempo drift is allowed, but otherwise tries to avoid jumping over 100ms at once. 
Confidence Bars - Bars drawn over the timeline showing candidate-match scores from the aligner. Their meaning depends on phase: acquiring confidence bars span the whole scan range at fixed ref-time coordinates (no lock yet to glide with); tracking confidence bars span a small window around the current position estimate and glide along with the position bar.

Notes - text information associate with a song. Can either be "Free Notes" or "Timeline Notes"
Free Notes - A large text area of free-form text associated with a specific song (no time element).
Timeline Notes - A small snippet of text that appears as an HTML element on the timeline at a specific time for a specific song.


Timeline Container - the full-width scrollable div that contains the timeline.
Timeline - A very wide tiled canvas that display's a song's vocal waveform, novocal waveform, and beats. Can also contain html elements that are associated with a point in time for the song.
Position Bar - a vertical bar that spans the full height of the timeline, and represents the current position in time of the song.
Auto-Scroll - When in the Auto-Scroll state, the timeline container auto-scrolls to align the position bar at a certain left-offset of the timeline container.
Timeline Padding - There is left-padding and right-padding that should have a sum width that matches the timeline container's width. This allows auto-scrolling to work properly near the start and end of songs.

# Architecture

The Show, song order, song notes, sync status, etc, should all be server state. This information is shared with the client, but ultimately the server is the source of truth.

The client has somewhat limited state scoped to the client, just the selected song and timeline container scroll position.

There should be API routes to load general info (song list, sync info, listener info, etc.) And there should be an API to load a specific song info.

However, there should also be web sockket connection that broadcasts changes to the general info and song info, so that clients get immediately updated.

# Layout
There's a thin navbar on the top edge. full width. It has the "Showtime Notes" brand, it shows what's currently synced, and option to configure the client as a listener,
The bottom half of the screen has the timeline plus some info/controls above the timeline.
The top-left contains the "menu". It contains a vertical stack of rows, and each row is a song. The top top has an option to record.
The top right contains the "selected song" information and free notes.

Syncing should be indicated by a svg icon of a straight arrow going right and below that an arrow going left. The arrows are yellow during the acquiring phase, and green during the tracking phase.

