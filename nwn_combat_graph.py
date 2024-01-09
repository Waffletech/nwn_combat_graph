#!/usr/bin/python3
import os
import argparse
import asciichartpy as acp
from textual.app import App
from textual.containers import ScrollableContainer
from textual.widgets import Footer, Static
from nwn_log_parser import NWNLogParser


class CombatGraph(Static):
    def __init__(self, graph_title, graph_data, **kwargs):
        super().__init__(**kwargs)
        self.border_title = graph_title
        self.graph_data = graph_data

    def render(self):
        self.columns = os.get_terminal_size().columns - 19
        return acp.plot(self.graph_data[-self.columns:], {'height': 10})
    
    
class NWNLogGraph(App):
    CSS_PATH = 'nwn_combat_graph.tcss'
    BINDINGS = [('escape', 'quit', 'Exit')]
    
    def __init__(self, character_name, log_filename):
        super().__init__()
        self.nwn_log_parser = NWNLogParser(character_name, log_filename)
        
    def compose(self):
        yield Footer()
        yield ScrollableContainer(
            CombatGraph('Healing per minute', self.nwn_log_parser.healing_per_min, id='healing'), 
            CombatGraph('Damage Dealt per minute', self.nwn_log_parser.damage_dealt_per_min, id='dmg_dealt'), 
            CombatGraph('Damage Taken per minute', self.nwn_log_parser.damage_taken_per_min, id='dmg_taken'),
            CombatGraph('Damage Mitigated per minute', self.nwn_log_parser.damage_mitigated_per_min, id='dmg_mitigated'),
            id='graph_container'
        )
        self.update_timer = self.set_interval(1.0, self.update_data)
    
    def action_quit(self):
        self.exit()
        
    def update_data(self) -> None:
        self.nwn_log_parser.update()
        container = self.get_child_by_id('graph_container')
        for c in container.children:
            if c.name == 'healing':
                c.graph_data = self.nwn_log_parser.healing_per_min
            elif c.name == 'dmg_dealt':
                c.graph_data = self.nwn_log_parser.damage_dealt_per_min
            elif c.name == 'dmg_taken':
                c.graph_data = self.nwn_log_parser.damage_taken_per_min
            elif c.name == 'dmg_mitigated':
                c.graph_data = self.nwn_log_parser.damage_mitigated_per_min
            c.refresh(repaint=True)
        

if __name__ == '__main__':
    argp = argparse.ArgumentParser(
        prog='nwn_combat_graph',
        description='A Python text application that parses NWN\'s client log and displays combat graphs.',
    )
    argp.add_argument('-n', '--name', required=True, help='Character name.')
    argp.add_argument('-l', '--log', default='./nwclientLog1.txt', help='Path to log file.')
    args = argp.parse_args()
    
    app = NWNLogGraph(character_name=args.name, log_filename=args.log)
    app.run()
