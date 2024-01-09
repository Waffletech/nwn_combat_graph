# nwn_combat_graph
A Python text application that parses NWN's client log and displays combat graphs.

## Installation
You need Python and the following modules installed:
pygtail, asciichartpy, textual

If you have pip you can install these packages from the command line:
```
pip install pygtail
pip install asciichartpy
pip install textual
```

## Usage
```
> python nwn_combat_graph.py -n 'Johnny Neverwinter' -l 'C:\Users\Me\Documents\Neverwinter Nights\logs\nwclientLog1.txt'
```

If you place these files in the log directory then you do not need to provide the `-l` or `--log` argument - it will look in the current directory for `nwclientLog1.txt`

## Known Bugs / Limitations

NWNLogParser currently doesn't parse damage types.

There were some issues in parsing log lines where the character name had `[DM]` in it. Rather than fix the splitting/parsing logic I chose to ignore those lines.
