# Environment Overseer

This small Python script allows one to execute arbitrary scripts based on environment conditions.

Goal of this project is to limit my own procrastination.

Example Setup:
 - Script `scripts/managers/youtube` reports seeing YouTube requests in Pi-hole's log
 - Overseer will consider the activity `YouTube` as enabled, tracking the time it has spent enabled
 - After YouTube's limit was reached, Overseer will execute `scripts/disable/youtube`
 and consider YouTube disabled

See this repo's `examples` for my own config files ( THEY ARE NOT DROP IN SCRIPTS. Most of them use either my docker setup or my nickname, they are just that - examples )

## Features

* [X] Rich possibilities for monitors, extensions, managers
* [X] Manual enabling / disabling activities
* [X] Automatic tracking of time spent on addiction prone sites
* [X] Automatic enabling / disabling activities based on time of day
* [X] Automatic enabling / disabling activities based on time spent
* [X] Checks and balances to make sure Overseer isn't tampered with

## Hardness

Thanks to multiple checks and hashsums, Overseer is pretty hardened out of the box. I have not found a trivial way how to cheat yet.

Some even more hardnening tips:
 - Make sure Overseer's unit has `RefuseManualStop=true`
 - Make sure you have `checks` scripts for existing activities
 	- Purpose of `checks` scripts is to get tripped when user tries to go over Overseer's head
	- e.g. a `checks/youtube` would check if YouTube is actually blocked
	- `checks` scripts are not neccessary but provide another level of safety against your lazy self

## Usage

`overseer`: Start main daemon of the app   
`overseer --forbidreset`: Start main daemon of the app, but also forces the app to ignore reset requests  
`overseer --enable <activity>`: Manually enables an activity  
`overseer --disable <activity>`: Manually disables an activity  
`overseer --reset`: Resets trackers for all activities (does nothing if daemon has `-f`)  
`overseer --list`: Prints currently active activities  
`overseer --prepare`: Prepares Overseer's file structure  
`overseer --tick`: Notifies Overseer of an update
`overseer --stop`: Gracefully stops Overseer 

## Testing

To make sure Overseer works, you can do
```
git clone https://github.com/richard-hajek/environment-overseer.git
cd environment-overseer
sudo docker-compose up
```

This will run end-to-end tests stored in `test/routine.sh`

## Installation & Configuration

To install Overseer and to configure it, please head over to 
[Overseer Wiki](https://github.com/meowxiik/environment-overseer/wiki) for configuration guide and examples.
