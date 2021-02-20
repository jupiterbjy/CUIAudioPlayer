# CUI Audio Player

---

Still under heavy development, expect tons of bugs.

- Python 3.8 ~ 3.9
- Requires ```master``` branch of [py_cui](https://github.com/jwlodek/py_cui)
- Requires CMD on Windows, changing font may be necessary.

*0.0.3a - dev*  
![](Demo/Images/Demo.webp)

---

## Intro

Meant to provide a way to play Audio file in headless configuration via SSH shell.

Ultimate goal is to stream soundtrack, but that's far, far way to go.
Currently, only application would be playing soundtrack from the speaker attached to headless server - which is rare
configuration.  

Although this project strictly follow PEP8 at my best, readability might not meet the standard.

You might want to change codepage when running on CMD. That way you can use utf-8 supported fonts.

---

## Usage

Clone this and run ```py CUIAudioPlayer```, *python*, *python3.9* or whatever python alias you are using.
May have to install the dependency manually.

- Audio List / Meta / Info (Widget) Common control:
    - *Space bar* : Pause / Resume track
    - *Left Arrow* : Move playback backward 5%
    - *Right Arrow* : Move playback forward 5%

- Audio List (Widget)
    - File explorer functionality: Select *DIR* marked items and press *Enter* to step in.
    - Play audio file: Select Audio track and press *Enter* to play it. Stops the previous track if there was any.

- Meta (Widget)
    - Scrolling up, down with *Arrow Up* and *Arrow Down*. Automatically display selected track's metadata.

- Info (Widget)
    - No interaction, currently users can edit the content, I have no control over it yet.

- Volume (Widget)
    - Select, press *Left* or *Right* to adjust volume. This just change multiply factor, might distort audio.

- Buttons
    - Play
      - Act as *Space* in *Audio List*.
    - Stop
      - Stops the current track and set playback to 0 second.  Resuming will play this stopped track from start.
    - Reload
      - Re-scan current folder. Stops the audio.
    - Previous
      - (Not implemented yet) Stop the current and play the previous track.
    - Next
      - Stop the current and play the next track.

Select folder you want to go or audio file you want to play, punch Enter.
Punching Enter again while playing will stop the currently playing track.

Pressing Space bar in that AudioList widget or pressing "Play" button will pause the track.
If there is no loaded audio then "Play" button, or space bar, will play the selected track.

---
## Background

This tiny project has goal of learning followings:
 - Modules
   - [py_cui](https://github.com/jwlodek/py_cui)
   - [py-sounddevice](https://github.com/spatialaudio/python-sounddevice)
   - [tinytag](https://github.com/devsnd/tinytag)
  
 - Book
   - Python Cookbook 3E
   - Fluent Python

Originally meant to create a testing bed for learning *sounddevice* module for use in project
 future projects inside [ProjectIncubator](https://github.com/jupiterbjy/ProjectIncubator), turns out that this module is
awesome. I'm having tons of fun with it.

Therefore, from *ProjectIncubator* I separated this using ```subtree split``` - totally a neat feature.

Additionally, I find [py_cui](https://github.com/jwlodek/py_cui) promising and suits my tastes a lot,
I decided to create a repo utilizing both.

Plus, this will be my first repo trying out git features such as milestones, issue, etc.

---
## Status

This impressive pre-stone-age program does:
- refresh audio list
- show *part* of metadata (No joke!)
- Other checked stuff mentioned below.

that's all.

---
## Planned features
Will mark those if it's implemented.
- [ ] Bare minimum audio player functions
    - [x] pause
    - [x] highlight current
    - [x] wrong file handling
    - [x] library navigation
    - [x] show progress
    - [x] Continues play - works mostly.
    - [ ] Shuffle
    - [x] Volume control (SW)
    - [x] Jump to section
    - [ ] Previous / Next track
    - [ ] mp3 / m4a support - might require pydub and conversion.
- [ ] Album art visualizing on some sort of ascii art.
- [ ] lrc support
- [ ] Show freq. map
- [ ] favorites
- [ ] Server - client stream

---
## Things to overcome / overcame

### 2-width characters on *py_cui*
  [This](Demo/Images/compare_before.png) is caused by some 2-digit characters such as some unicode symbols or CJK letters.
  For now, I used *wcwidth* module to determine actual string length and add trailing ZWSP on each of those letters.
  With actual length and *len()* length now matches, and by slicing and striping outcome - py_cui now don't break up
  like above, at least on certain environments - as shown below.
 
### Dynamic updating of texts
  As I shorten each lines for each widget to prevent py_cui breaking like above, layouts, I need to make a way to
  remember each lines and cycle per line basis to let your see full name of the file. Without help of event loops like
  *trio*, this might get non-straightforward and complicated to implement it.

### Inconsistent ZWSP and string legnth on Win10 environment
  [Example](Demo/Images/trouble_1.png) footage of curses module at finest.  
  Actually I should pad string in reverse order, but just for an example.
 
  Tested out all the terminals I can find for Win10, but none of them have consistent output like real linux terminal. 
  The only working combination is *WSL2* + *Windows Terminal* or pure *CMD*.
  
  *CMD* + *Windows Terminal*
  can't handle ZWSP either. Since I can't use *sounddevice* on *WSL* yet - until I implement server-client,
  configuration I am stuck with CMD.
