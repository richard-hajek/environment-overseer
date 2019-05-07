# Environment Overseer

This small Python script allows one to control their environment.
It uses user-defined enable and disable scripts and internal timer to run these scripts as per user specification.

## Examples

* [X] Limit internet to x hours a day
* [X] Limit Steam to y hours a day
* [X] Limit YouTube to z hours a day
* [X] And much more


## Usage

`overseer`: Start main daemon of the app.  
`overseer -e <activity>`: Enables an activity  
`overseer -d <activity>`: Disables an activity  
`overseer -r`: Resets the time intervals for all activities  
`overseer -w`: Copies folder `today` to dedicated `history` folder, useful for keeping a history

In examples above, `<activity>` is always a name of an activity.

`overseer`, `overseer -r` nor `overseer -w` will not be ran automatically, yet they are designed to be.
Thus it is advisable to run these automatically, either using systemd or cron.
All commands need a prior `overseer` to be running. There can only be one `overseer` running at one time, preferably all the time.


## Structure

Anything can be blocked, as long as you have a script to block it and script to unblock it.
These go to `scripts/enable/<activity>` and `scripts/disable/<activity>`.
Last file you need is `limits/<activity>` which should contain the time one is allowed to leave an activity enabled, in seconds.

Ergo, the total structure is as following:
```
EnvironmentOverseer
├── limits
│   └── <activity>
├── scripts
│   ├── disable
│   │   └── <activity>
│   └── enable
│       └── <activity>
├── today
│   └── <activity> # Auto generated, do not create, contains number of seconds activity spent enabled
└── active
    └── <activity> # Only exists if the activity is currently enabled
```

In examples above `<activity>` is always a single file, named by the activity itself.

Folders `today` and `active` are both runtime generated, you should only read from those.
They are refreshed every ~60 seconds.