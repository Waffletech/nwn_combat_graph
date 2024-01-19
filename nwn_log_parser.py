import os
from datetime import timedelta
from dateutil import parser
from pygtail import Pygtail


def _daterange(start_date, end_date):
    # We want to iterate over every minute
    for n in range(int((end_date - start_date).seconds / 60) + 1):
        yield start_date + timedelta(minutes=n)


class NWNLogParser():
    """
    Parses NWN's nwnclientLog1.txt and extracts some potentially useful combat statistics from it.
    
    The rawest parsed data is in:
        damage
        healing
        mitigation
        experience
        
    damage is further categorized in two properties for convenience
    damage still contains all of the damage events, these are subsets of that:
        damage_dealt
        damage_taken
        
    These all have the following structure:
        time: The timestamp of this event
        time_min: The timestamp of this event rounded down to the minute
        source: The source of this effect
        amount: How much healing, damage, xp etc
    The damage data also has:
        target: who was the damage applied to?
        types: dictionary of damage types and amounts
            example: 
            {
                'Cold': 10,
                'Negative Energy': 2,
            }
        
    Usage:
        nwn = NWNLogParser('Johnny Neverwinter')
        
        sleep(10.0)
        # read any new log entries
        nwn.update()
        
        total_dmg = sum([d['amount'] for d in nwn.damage_dealt])
        print(f'Total damage dealt: {total_dmg}')
    """
    def __init__(self, character_name: str, log_filename:str = './nwclientLog1.txt') -> None:
        self.character_name = character_name
        self.log_filename = log_filename
        
        self.damage = []
        self.healing = []
        self.damage_dealt = []
        self.damage_taken = []
        self.mitigation = []
        self.experience = []
        self.min_time = None
        self.max_time = None
        
        self.healing_per_min = []
        self.damage_dealt_per_min = []
        self.damage_taken_per_min = []
        self.damage_mitigated_per_min = []
        self.experience_per_min = []

        if os.path.exists(f'{self.log_filename}.offset'):
            os.remove(f'{self.log_filename}.offset')
        self.update()
        

    def _parse_log_line(self, line):
        line = line.strip()
        # There might be multi-line logs from chat/sys messages. We only care about single-line combat messages
        if '[CHAT WINDOW TEXT]' in line:
            l = line.split('] ')
            t0 = l[1][1:]
            if ']' in t0:
                t0 = t0.replace(']', '')
            t = parser.parse(t0)
            t_m = t.replace(second=0)
            if not self.min_time or t_m < self.min_time:
                self.min_time = t_m
            if not self.max_time or t_m > self.max_time:
                self.max_time = t_m
            # Make sure this isn't a placeable/npc speaking with the word ' damages ' in it
            if ' damages ' in line and '[DM]' not in line and '(' in line and ')' in line:
                # [CHAT WINDOW TEXT] [Sun Jan  7 12:17:03] Narwen Alendiel damages Melek Scavenger: 10 (10 Cold)
                # l = line.split('] ')
                damage_entry = {}
                damage_entry['time'] = t
                damage_entry['time_min'] = t_m
                damage_entry['source'] = l[2].split(' damages ')[0]
                damage_entry['target'] = l[2].split(' damages ')[1].split(': ')[0]
                damage_entry['amount'] = int(l[2].split(' damages ')[1].split(': ')[1].split(' (')[0])
                damage_entry['types'] = self._parse_damage_types(l[2].split(' damages ')[1].split(': ')[1].split(' (')[1][0:-1])
                self.damage.append(damage_entry)
                if damage_entry['source'] == self.character_name:
                    self.damage_dealt.append(damage_entry)
                if damage_entry['target'] == self.character_name:
                    self.damage_taken.append(damage_entry)
            elif ' : Healed ' in line and '[DM]' not in line:
                # [CHAT WINDOW TEXT] [Sun Jan  7 12:17:20] Atticus Naros : Healed 2 hit points.
                # l = line.split('] ')
                heal_entry = {}
                heal_entry['time'] = t
                heal_entry['time_min'] = t_m
                heal_entry['source'] = self.character_name
                heal_entry['target'] = l[2].split(' : Healed ')[0]
                heal_entry['amount'] = int(l[2].split(' : Healed ')[1].replace(' hit points.', ''))
                self.healing.append(heal_entry)
            elif f'{self.character_name} : Damage Immunity absorbs ' in line:
                # [CHAT WINDOW TEXT] [Tue Jan  9 11:30:46] Narwen Alendiel : Damage Immunity absorbs 1 point(s) of Physical
                mit_entry = {}
                mit_entry['time'] = t
                mit_entry['time_min'] = t_m
                mit_entry['amount'] = int(l[2].split(': Damage Immunity absorbs ')[1].split(' ')[0])
                self.mitigation.append(mit_entry)
            elif f'{self.character_name} : Damage Reduction absorbs ' in line:
                # [CHAT WINDOW TEXT] [Tue Jan  9 11:30:46] Narwen Alendiel : Damage Reduction absorbs 5 damage
                mit_entry = {}
                mit_entry['time'] = t
                mit_entry['time_min'] = t_m
                mit_entry['amount'] = int(l[2].split(': Damage Reduction absorbs ')[1].split(' ')[0])
                self.mitigation.append(mit_entry)        
            elif 'Experience Points Gained:' in line:
                # [CHAT WINDOW TEXT] [Sat Aug 19 15:04:05] Experience Points Gained:  1
                exp_entry = {}
                exp_entry['time'] = t
                exp_entry['time_min'] = t_m
                exp_entry['amount'] = int(l[2].split('Experience Points Gained:')[1])
                self.experience.append(exp_entry)

    def _parse_damage_types(self, text):
        # Parse a space separated string:
        #   1 Fire 2 Cold
        # Complexity arises that the damage name can have spaces in it too
        #   1 Negative Energy 2 Fire 1 Cold
        # This isn't the most elegant algorithm
        damage_dict = {}
        digits = '0123456789'
        damage_amount = ''
        damage_type = ''
        for i in range(0, len(text)):
            if text[i] in digits:
                # if we have a damage_type that means we've switched from non-digits back to digits
                # we can store this in the dict before clearing damage_type out
                if damage_type != '':
                    damage_dict[damage_type.strip()] = int(damage_amount)
                    damage_type = ''
                damage_amount += text[i]
            elif text[i] != ' ':
                # Capture everything else in damage_type, including spaces 
                # We strip leading/trailing spaces later
                damage_type += text[i]
        # We don't switch back from non-digits to digits for the last (or singular) entry
        # Capture that here
        if damage_type.strip() != '':
            damage_dict[damage_type.strip()] = int(damage_amount)
        return damage_dict
    
    def update(self):
        for line in Pygtail(self.log_filename, encoding='cp850'):
            self._parse_log_line(line)

        # update sums and totals
        self.healing_per_min.clear()
        self.damage_dealt_per_min.clear()
        self.damage_taken_per_min.clear()
        self.damage_mitigated_per_min.clear()
        self.experience_per_min.clear()
        
        if self.min_time is None and self.max_time is None:
            # This can happen when the nwn client was started but no games/servers were joined
            pass
        else:
            for h in _daterange(self.min_time, self.max_time):
                healing_this_min = 0
                damage_dealt_this_min = 0
                damage_taken_this_min = 0
                damage_mitigated_this_min = 0
                xp_this_min = 0
                
                for x in self.healing:
                    if x['time_min'] == h:
                        healing_this_min += x['amount']
                for x in self.damage_dealt:
                    if x['time_min'] == h:
                        damage_dealt_this_min += x['amount']
                for x in self.damage_taken:
                    if x['time_min'] == h:
                        damage_taken_this_min += x['amount']
                for x in self.mitigation:
                    if x['time_min'] == h:
                        damage_mitigated_this_min += x['amount']
                for x in self.experience:
                    if x['time_min'] == h:
                        xp_this_min += x['amount']
                
                self.healing_per_min.append(healing_this_min)
                self.damage_taken_per_min.append(damage_taken_this_min)
                self.damage_dealt_per_min.append(damage_dealt_this_min)
                self.damage_mitigated_per_min.append(damage_mitigated_this_min)
                self.experience_per_min.append(xp_this_min)
        