# Environment Overseer

This small Python script allows one to execute other scripts based on environment conditions.

Goal of this project is to limit my own procrastination, using scripts to detect if one is for example watching 
YouTube and record this, possibly block if YouTube's limit was reached.

Overseer is designed to run on a upstream network device (router) to be able to intercept and block traffic. (Tested with PiHole)

Anything can be blocked, as long as you have a script to block it and script to unblock it.

## Capabilities
* [X] Manual enabling / disabling of activities
* [X] Keeping track of activity enabled time
* [X] Automatic enabling / disabling activities based on time of day
* [X] Checking whether system is conformant to enable / disable scripts, executing them again if not

## Usage

`overseer`: Start main daemon of the app  
`overseer -e <activity>`: Enables an activity  
`overseer -d <activity>`: Disables an activity  
`overseer -r`: Resets timers for all activities  
`overseer -l`: Prints currently active activities (Effectively `ls /etc/overseer/status`)  
`overseer -p`: Prepares Overseer's file structure

## JSON Activity Definition

Activity definition must be a `.json` file with `json` structure in folder `/etc/overseer/activities/`.
Overseer supports following properties:

`Limit`: When activity reaches limit set by this property, it is automatically disabled and it's enabling is blocked. Format must match following `integer{H,h,S,s,M,m}`

`AutoStart`: Activity will be automatically enabled at this time. Time in format `%H:%M`.

`AutoStop`: Activity will be automatically disabled at this time. Same format as `AutoStart`

Note that `AutoStart` and `AutoStop` do not force keep the activity enabled or disabled.
It's the equivalent of executing `overseer -e` at `AutoStart` or `overseer -d` at `AutoStop`

###Examples
```
{
    "Limit": "30M"
}
```

```
{
    "Limit": "3H", 
    "AutoStart":"14:00",
    "AutoStop":"16:00"
}
``` 

## Example configuration

Requisites:
* Linux device with it's own AP (ArchLinux preferably, but not necessarily)
* PiHole on this device
* Overseer

Description:
 * Let's setup blocking of YouTube, allowing it only for 30 minutes a day

WiFi & PiHole setup:
 * Wireless AP on your Linux machine guide [(link)](https://wiki.archlinux.org/index.php/Software_access_point)
 * PiHole guide [(link)](https://wiki.archlinux.org/index.php/Pi-hole)

Setup Overseer:
1. Download EnvironmentOverseer
    * `git clone https://gitlab.com/meowxiik/environment-overseer.git/`
2. Copy EnvironmentOverseer to executable location
    * `cd environment-overseer`
    * `sudo cp overseer /usr/bin/`
3. Run `overseer -p`
4. Populate folders in /etc/overseer

##### `/etc/overseer/activities/youtube`
``` 
{
    "Limit": "30M"
}
```

##### `/etc/overseer/scripts/exec/youtube`
```
#!/usr/bin/bash

pihole -w -nr youtube.com
pihole -w -nr www.youtube.com
pihole -w -nr youtubei.googleapis.com
pihole --wild -d -nr googlevideo.com

pihole restartdns
```

##### `/etc/overseer/exec/disable/youtube`
```
#!/usr/bin/bash

pihole -b -nr youtube.com
pihole -b -nr www.youtube.com
pihole -b -nr youtubei.googleapis.com
pihole --wild -nr googlevideo.com

pihole restartdns
```

Now you are ready!
Run `sudo overseer &` to start it in background and if you go to your workstation connected to the AP
you should not have access to YouTube!

And try `sudo overseer -e youtube`, now if you refresh, YouTube will be enabled!

## Structure

File Structure:
```
/etc/overseer/
├── activities
│   └── <activity>.json
├── exec
│   ├── disable
│   │   └── <activity>
│   ├── enable
│   │   └── <activity>
│   ├── status # Optional
│   │   └── <activity>
│   └── triggers # Optional
│       └── <activity>
├── timers
│   └── <activity> # Auto generated
├── rev_timers
│   └── <activity> # Auto generated
└── status
    └── <activity>
```

In examples above `<activity>` is always a single file, named by the activity itself.

### Description of file structure:

`activities/<activity>.json` - 
Main configuration file of activity, contains "Limit" and "Auto" timers.

`exec/disable/<activity>` - 
Script to disable the activity.

`exec/enable/<activity>` - 
Script to enable the activity.

`exec/status/<activity>` - 
Used to guard whether the system conditions hadn't changed, e.g. in a process crash.
This script should examine the system and report whether the activity is actually enabled or disabled, regardless of what overseer thinks.
If this report will be in conflict with what overseer thinks, overseer will take action to fix it.

`exec/triggers/<activity>` - Script, that if returns 1, the activity will be enabled, 0 activity will be disabled.

`timers/<activity>` - Contains number of seconds an activity spent enabled.
**Auto generated and managed**

`rev_timers/<activity>` - Contains number of seconds activity has left until limit.
**Auto generated and managed**

`status/<activity>` - A symlink to `activities/<activity>.json`, represents enabled activity.
**Managed, but manual interference is possible**