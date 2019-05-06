# Environment Overseer

This small batch of Python scripts allows one to control their environment. It is useful, if you want to limit exposure to certain activities or influences (internet, etc...).

## Examples

* [X] Limit internet to x hours a day
* [X] Limit Steam to y hours a day
* [X] Limit YouTube to z hours a day
* [X] And much more


## Usage

`timer` needs to be running in order for the app to work, I recommend creating a systemd service for it.  
`enable <activity>` enables an activity  
`disable <activity>` disables an activity

## Structure

Anything can be blocked, as long as you have a script to block it and script to unblock it.
These go to `scripts/enable/<name>` and `scripts/disable/<name>`.
Last file you need is `limits/<name>` which should contain the time one is allowed to leave an activity enabled, in seconds.

Ergo, the total structure is as following:
```
EnvironmentOverseer
├── limits
│   └── <name>
├── scripts
│   ├── disable
│   │   └── <name>
│   └── enable
│       └── <name>
└── today
    └── <name> # Auto generated, do not create
```

File in `today` will be generated automatically and contains number of seconds left, you may use this to read how much time is left. It refreshes every ~60 seconds.

See my defined limits for examples.