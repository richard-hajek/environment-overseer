# Environment Overseer

This small Python script allows one to execute arbitrary scripts based on environment conditions.

Goal of this project is to limit my own procrastination.

Example Setup:
 - Script `scripts/managers/youtube` reports seeing YouTube requests in Pi-hole's log
 - Overseer will consider the activity `YouTube` as enabled, tracking the time it has spent enabled
 - After YouTube's limit was reached, Overseer will execute `scripts/disable/youtube`
 and consider YouTube disabled

## Capabilities

* [X] Automatic tracking of time spent on addiction prone sites
* [X] Automatic enabling / disabling activities based on time of day
* [X] Automatic enabling / disabling activities based on time spent
* [X] Manual enabling / disabling activities

## Installation

Arch Linux:
Use [AUR package](https://aur.archlinux.org/packages/environment-overseer-git/)

Others:
1. Clone this repo
2. Copy executable from `src` to your preferred directory in PATH
3. (Recommended) Copy systemd units from `systemd` to `/etc/systemd/system`

## Usage

`overseer`: Start main daemon of the app   
`overseer -e <activity>`: Manually enables an activity  
`overseer -d <activity>`: Manually disables an activity  
`overseer -r`: Resets trackers for all activities  
`overseer -l`: Prints currently active activities (Effectively `ls /etc/overseer/enabled`)  
`overseer -p`: Prepares Overseer's file structure

## Example configuration

Description:
 * Let's setup blocking of YouTube, allowing it only for 30 minutes a day, using Pi-hole
 * Follow these steps on a machine that will be the **DNS server**

1. Setup Pi-hole, use [ArchWiki - Pi-hole](https://wiki.archlinux.org/index.php/Pi-hole)
 - Step [Making devices use Pi-hole](https://wiki.archlinux.org/index.php/Pi-hole#Making_devices_use_Pi-hole) is very important.
2. Install Overseer
3. Run `overseer --prepare`
4. Clone the repo
 - `git clone https://gitlab.com/meowxiik/environment-overseer.git/`
 - `cd environment-overseer`
5. Copy example files
 - `cp examples/activities/youtube.json /etc/overseer/activities/`
 - `cp examples/scripts/enable/youtube /etc/overseer/scripts/enable/youtube`
 - `cp examples/scripts/disable/youtube /etc/overseer/scripts/disable/youtube`
 - `cp examples/scripts/managers/youtube /etc/overseer/scripts/managers/youtube`
6. Start the Overseer! `sudo systemctl enable overseer` or simply `overseer`.

Now you are ready!
Switch to the DNS server and try watching YouTube, you should only get around 30 minutes!

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
Main configuration file of activity, contains "Limit" and "AutoStart" and "AutoStop".

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

### Creating your own scripts

1. Create `json` definition file.   

This file has to be named `<activity_name>.json` and must be placed inside `/etc/overseer/activities`.
This file has to contain either `Limit` property or `AutoStart` and `AutoStop` properties.

```json
{
	"AutoStart": "08:20",
	"AutoStop": "09:00"
}
```

```json
{
	"Limit": "1H"
}
```

2. Create enable and disable scripts.  

These must go to `/etc/overseer/scripts/enable` and `/etc/overseer/scripts/disable` respectively.
Their names must match the activity's.
No return value is expected from these scripts.
Once this script runs, activity is considered to have changed state.

3. (Recommended) Create a manager script

This script is used for automatic enabling / disabling of activities.
The job of this script is to report whether user wants to use a site.
This script must go to `/etc/overseer/scripts/managers`.
It's name must match the activity's.
If the script returns `0` activity is enabled, if the script returns `1` activity is disabled.
Usually what I do is `tail` the DNS log of Pi-hole to see if the site is in use, attempt to enable if yes.
(Overseer will watch the limit on it's own, it is not the job of this script, that is, 
this script should try to enable the activity even if it is out of limit)
