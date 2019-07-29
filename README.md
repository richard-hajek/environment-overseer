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
* [X] Manual enabling / disabling activities

## Installation

Arch Linux:
Use [AUR package](https://aur.archlinux.org/packages/environment-overseer-git/)

Others:
Clone this repo, executables are in `src`

## Usage

`overseer.py`: Start main daemon of the app   
`overseer.py -e <activity>`: Enables an activity  
`overseer.py -d <activity>`: Disables an activity  
`overseer.py -r`: Resets timers for all activities  
`overseer.py -l`: Prints currently active activities (Effectively `ls /etc/overseer/enabled`)  
`overseer.py -p`: Prepares Overseer's file structure

## Example configuration on Arch Linux

Description:
 * Let's setup blocking of YouTube, allowing it only for 30 minutes a day, using Pi-hole

1. Setup Pi-hole, use [ArchWiki - Pi-hole](https://wiki.archlinux.org/index.php/Pi-hole)
 - Step [Making devices use Pi-hole](https://wiki.archlinux.org/index.php/Pi-hole#Making_devices_use_Pi-hole) is very important.
2. Install Overseer
3. Run `overseer.py --prepare`
4. Clone the repo
 - `git clone https://gitlab.com/meowxiik/environment-overseer.git/`
 - `cd environment-overseer`
5. Copy example files
 - `cp examples/activities/youtube.json /etc/overseer/activities/`
 - `cp examples/scripts/enable/youtube /etc/overseer/scripts/enable/youtube`
 - `cp examples/scripts/disable/youtube /etc/overseer/scripts/disable/youtube`
 - `cp examples/scripts/managers/youtube /etc/overseer/scripts/managers/youtube`

Now you are ready! Try watching YouTube, you should only get around 30 minutes of YouTube!

Other example configurations include: Discord, Facebook, Netflix, Reddit

## Structure

File Structure:
```
/etc/overseer/
├── activities
│   └── <activity>.json
├── enabled
│   └── <activity>
├── ready
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

`enabled/<activity>` -
A symlink to `activities/<activity>.json`, represents enabled activity.

`ready/<activity>` -
A symlink to `activities/<activity>.json`, represents a stand-by activity.
(Activity which is Enabled, but is not used and is not being counted)

`scripts/disable/<activity>` - 
Script to disable the activity.

`scripts/enable/<activity>` - 
Script to enable the activity.

`trackers/<activity>` -
 Contains number of seconds an activity spent enabled.

`reverse-trackers/<activity>` -
 Contains number of seconds activity has left until limit.

`scripts/managers/<activity>` -
Used to watch an activity. It is a script that should return 0 if activity should enable
or 1 if activity should be in stand-by state.
