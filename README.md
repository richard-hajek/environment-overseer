# Environment Overseer

This small Python script allows one to execute other scripts based on environment conditions.

Goal of this project is to limit my own procrastination, using scripts to detect if one is for example watching 
YouTube and record this, possibly block if YouTube's limit was reached.

Overseer is designed to run on a upstream network device (router) to be able to intercept and block traffic. (Tested with PiHole)

Anything can be blocked, as long as you have a script to block it and script to unblock it.

## Capabilities

* [X] Automatic tracking of time spent on addiction prone sites
* [X] Automatic enabling / disabling activities based on time of day
* [X] Automatic enabling / disabling activities based on time spent

## Installation

Arch Linux: 
- Use [AUR package](https://aur.archlinux.org/packages/environment-overseer-git/)

Other:
- Run `git clone https://gitlab.com/meowxiik/environment-overseer.git/`
- `cd environment-overseer`
- Move *src/overseer.py* into an executable directory `mv src/overseer.py /usr/local/bin/overseer.py`
- Move *systemd/** into a systemd directory `mv systemd/* /etc/systemd/system`

## Usage

`overseer`: Start main daemon of the app   
`overseer -e <activity>`: Enables an activity  
`overseer -d <activity>`: Disables an activity  
`overseer -r`: Resets timers for all activities  
`overseer -l`: Prints currently active activities (Effectively `ls /etc/overseer/status`)  
`overseer -p`: Prepares Overseer's file structure

## Example configuration on Arch Linux

Description:
 * Let's setup blocking of YouTube, allowing it only for 30 minutes a day
 
Requisites:
* Arch Linux computer capable of hosting an access point

1. Setup portable WiFi Hotspot, use [this](https://wiki.archlinux.org/index.php/Software_access_point) if necessary
2. Setup PiHole, use [this](https://wiki.archlinux.org/index.php/Pi-hole) page
3. Install Overseer
4. Run `overseer --prepare`
5. Move example files:
 - `git clone https://gitlab.com/meowxiik/environment-overseer.git/`
    - You dont have to do this if you already downloaded the repo in installation
 - `cd environment-overseer`
 - `cp examples/activities/youtube.json /etc/overseer/activities/`
 - `cp examples/scripts/enable/youtube /etc/overseer/scripts/enable/youtube`
 - `cp examples/scripts/disable/youtube /etc/overseer/scripts/disable/youtube`
 - `cp examples/scripts/managers/youtube /etc/overseer/scripts/managers/youtube`

Now you are ready!

Connect to your WiFi and you should only get about half an hour of YouTube!

## Structure

File Structure:
```
/etc/overseer/
├── activities
│   └── <activity>.json
├── status
│   └── <activity>
├── scripts
│   ├── disable
│   │   └── <activity>
│   ├── enable
│   │   └── <activity>
│   ├── managers 
│   │   └── <activity> # Optional
│   └── extensions
│       └── <extension> # Extensions optional
├── trackers
│   └── <activity> # Auto generated
└── reverse-trackers
    └── <activity> # Auto generated
```

### Description of file structure:

`activities/<activity>.json` - 
Main configuration file of activity, contains "Limit" and "Auto" timers.

`status/<activity>` -
A symlink to `activities/<activity>.json`, represents enabled activity.

`scripts/disable/<activity>` - 
Script to disable the activity.

`scripts/enable/<activity>` - 
Script to enable the activity.

`trackers/<activity>` -
 Contains number of seconds an activity spent enabled.

`reverse-trackers/<activity>` -
 Contains number of seconds activity has left until limit.

`scripts/managers/<activity>` -
Used to control an activity, a script that return 0 if activity should enable or 1 if activity should disable.

