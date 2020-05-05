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
* [x] GUARDIAN System to protect Overseer's data from your tampering 

## Usage

`overseer`: Start main daemon of the app   
`overseer -e <activity>`: Manually enables an activity  
`overseer -d <activity>`: Manually disables an activity  
`overseer -r`: Resets trackers for all activities  
`overseer -l`: Prints currently active activities  
`overseer -p`: Prepares Overseer's file structure  
`overseer -t`: Notifies Overseer of an update (Forces a **t**ick to process)

## TODO

[-] Publish scripts

## Installation & Configuration

To install Overseer and to configure it, please head over to 
[Overseer Wiki](https://github.com/meowxiik/environment-overseer/wiki) for configuration guide and examples.
