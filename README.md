## CUI Audio Player

Just a tiny project to create a script that literally does its name.

Only working configurations are Linux Terminal / CMD / Windows Terminal + WSL.
Will show as broken on other configurations on Win10.

Although this project strictly follow PEP8 at best, readability might not.

*0.0.2a - 2x speed*  
![](Demo/Images/Demo.webp)

---
## Background

This tiny project has goal of learning followings:
 - Modules
   - [py_cui](https://github.com/jwlodek/py_cui)
   - [py-sounddevice](https://github.com/spatialaudio/python-sounddevice)
   - [tinytag](https://github.com/devsnd/tinytag)
 - 

Originally meant to create a testing bed for learning *sounddevice* module for use in project
 future projects inside [ProjectIncubator](github.com/jupiterbjy/ProjectIncubator), turns out that this module is
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
- play & stop, half-broken pause.

that's all.

---
## Planned features
Will mark those if it's implemented.
- [ ] Bare minimum audio player functions
    - [x] pause
    - [x] highlight current
    - [x] wrong file handling
    - [ ] library navigation
    - [x] show progress - Temporarily using seconds.
    - [x] Continues play - Half broken, but works mostly.
    - [ ] Shuffle
- [ ] Album art visualizing on some sort of ascii art.
- [ ] lrc support
- [ ] Show freq. map
- [ ] favorites

---
## Things to overcome / overcame

### *py_cui*'s lack of support for 2-width characters
  ![](Demo/Images/compare_before.png)  
  This is caused by some 2-digit characters such as some unicode symbols or CJK letters.
  For now, I used *wcwidth* module to determine actual string length and add trailing ZWSP on each of those letters.
  With actual length and *len()* length now matches, and by slicing and striping outcome - py_cui now don't break up
  like above, at least on certain environments - as shown below.
 
### Dynamic updating of texts
  As I shorten each lines for each widget to prevent py_cui breaking like above, layouts, I need to make a way to
  remember each lines and cycle per line basis to let your see full name of the file. Without help of event loops like
  *trio*, this might get non-straightforward and complicated to implement it.

### Inconsistent ZWSP and string legnth on Win10 environment
  ![](Demo/Images/trouble_1.png)  
  Example footage of curses module at finest. Actually I should pad string in reverse order, but just for an example.
 
  I eventually failed to satisfy *sounddevice*'s dependency - *PortAudio* - on *WSL2*, and since my linux server is
  headless & tongueless, I can't test there either. This is primary reason why I am using bare CMD mostly. 

  Tested out all the terminals I can find for Win10, but none of them have consistent output like real linux terminal. 
  The only working combination is *WSL2* + *Windows Terminal* or pure *CMD*. *CMD* + *Windows Terminal*
  can't handle ZWSP either. Since I can't use *sounddevice* on linux yet - until I implement server-client,
  configuration I amd stuck with CMD. I might be better check if I can fix this on
  *py_cui* side, might become somewhat dirty if I ever managed to do so.

### Understanding how callback works in sounddevice.OutputStream
  To see how dumb I am - check [this](https://github.com/spatialaudiKo/python-sounddevice/issues/306) out.
  Huge thanks to dev!
