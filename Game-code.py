import random
import time

# --- Constants ---
ALL_PLAYERS_COLORS = ["Red", "Blue", "Green", "Yellow", "Pink", "Orange", "Black", "White", "Purple", "Cyan"]
MIN_PLAYERS = 4 
MAX_PLAYERS = len(ALL_PLAYERS_COLORS)

# Locations and Tasks
LOCATION_TASKS = {
    "Electrical": ["fixing wires", "diverting power", "calibrating distributor"],
    "Cafeteria": ["emptying trash", "downloading data", "cleaning vent"],
    "Engine Room": ["fueling engines", "aligning engine output", "stabilizing steering"],
    "Admin": ["swiping card", "uploading data", "fixing weather nodes"],
    "Shields": ["priming shields", "clearing asteroids (manned)"],
    "Storage": ["organizing boxes", "fueling engines (lower/upper)"],
    "Medbay": ["submitting scan", "inspecting samples"],
    "Weapons": ["clearing asteroids", "downloading data", "accepting diverted power"],
    "Navigation": ["charting course", "stabilizing steering", "downloading data"],
    "Reactor": ["starting reactor", "unlocking manifolds", "diverting power"],
    "Security": ["monitoring cameras", "fixing wiring"],
    "Communications": ["resetting comms", "downloading data"],
    "O2": ["cleaning O2 filter", "emptying garbage", "filling canisters"]
}
ROOMS = list(LOCATION_TASKS.keys())

# Roles
ROLE_CREWMATE = "Crewmate"
ROLE_IMPOSTOR = "Impostor"
ROLE_MEDIC = "Medic"
ROLE_DETECTIVE = "Detective"

# Probabilities & Settings
SIGHTING_PROBABILITY = 0.5
SIGHTING_IMPOSTOR_BIAS = 0.4
SIGHTING_VICTIM_BIAS = 0.3
MEDIC_SCAN_ACCURACY = 1.0 
DETECTIVE_CLUE_ACCURACY = 0.80 
IMPOSTOR_LIE_QUALITY = 0.75 
CREWMATE_ACCUSATION_ACCURACY = 0.25 
SABOTAGE_CHANCE = 0.33
SABOTAGE_LIGHTS_OUT_SIGHTING_REDUCTION = 0.5

# --- Helper Functions ---
def print_separator(character="=", length=60):
    print(character * length)

def typewriter_print(text, delay=0.03):
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

# --- Classes ---
class Player:
    def __init__(self, name, game):
        self.name = name
        self.game = game 
        self.role = ROLE_CREWMATE
        self.is_alive = True
        self.tasks = [] 
        self.completed_tasks_count = 0
        self.current_location = None 
        self.current_task_description = "wandering" 
        self.alibi_location = None 
        self.alibi_task = "no specific task" 
        self.special_role_info = "" 

    def assign_tasks(self, num_tasks=3):
        self.tasks = []
        self.completed_tasks_count = 0
        possible_tasks_locations = list(self.game.location_tasks.keys())
        random.shuffle(possible_tasks_locations)

        for i in range(num_tasks):
            if not possible_tasks_locations: break
            loc = possible_tasks_locations.pop()
            if self.game.location_tasks[loc]:
                task_desc = random.choice(self.game.location_tasks[loc])
                self.tasks.append({"location": loc, "task": task_desc, "completed": False})

    def set_initial_alibi_and_current_state(self):
        if self.role != ROLE_IMPOSTOR and self.tasks:
            first_task = self.tasks[0]
            self.current_location = first_task['location']
            self.current_task_description = first_task['task']
        else: 
            self.current_location = random.choice(self.game.rooms)
            self.current_task_description = random.choice(self.game.location_tasks[self.current_location]) if self.game.location_tasks[self.current_location] else "looking busy"

        self.alibi_location = self.current_location
        self.alibi_task = self.current_task_description

    def __str__(self):
        role_str = f" ({self.role})" if self.game.game_over else ""
        status_str = "" if self.is_alive else " (Deceased)"
        return f"{self.name}{status_str}{role_str}"


class Game:
    def __init__(self, num_players=7, num_impostors=1):
        self.num_players = max(MIN_PLAYERS, min(num_players, MAX_PLAYERS))
        self.num_impostors = num_impostors if 1 <= num_impostors < self.num_players // 2 else 1
        
        player_names = random.sample(ALL_PLAYERS_COLORS, self.num_players)
        self.players = [Player(name, self) for name in player_names]
        
        self.location_tasks = LOCATION_TASKS
        self.rooms = ROOMS
        self.impostors = [] 
        self.victim = None  
        self.reporter = None 
        self.murder_room = None 
        self.fact_log = [] 
        self.game_over = False
        self.sabotage_active = None 
        self.round_sightings = [] 

    def get_player_by_name(self, name):
        for player in self.players:
            if player.name.lower() == name.lower():
                return player
        return None

    def get_alive_players(self):
        return [p for p in self.players if p.is_alive]

    def get_alive_crewmates(self): 
        return [p for p in self.get_alive_players() if p.role != ROLE_IMPOSTOR]

    def _assign_roles(self):
        print_separator("-")
        typewriter_print("Assigning roles secretly...")
        time.sleep(0.5)
        
        available_for_impostor = list(self.players)
        random.shuffle(available_for_impostor)

        for _ in range(self.num_impostors):
            if available_for_impostor:
                impostor_player = available_for_impostor.pop()
                impostor_player.role = ROLE_IMPOSTOR
                self.impostors.append(impostor_player)

        crew_for_special_roles = [p for p in available_for_impostor] 
        random.shuffle(crew_for_special_roles)

        if crew_for_special_roles:
            medic_player = crew_for_special_roles.pop()
            medic_player.role = ROLE_MEDIC
        if crew_for_special_roles: 
            detective_player = crew_for_special_roles.pop()
            detective_player.role = ROLE_DETECTIVE
        
        typewriter_print("Roles assigned.", 0.02)
        if self.num_impostors > 1:
            typewriter_print(f"There are {self.num_impostors} impostors among us.", 0.02)
        else:
            typewriter_print("There is 1 impostor among us.", 0.02)

    def _setup_round(self):
        self.fact_log = ["--- Round Start ---"] # game_over is NOT reset here
        self.round_sightings = []
        self.sabotage_active = None 

        for player in self.players:
            # is_alive is managed by ejection/kill, not reset per round unless new game
            if player.role != ROLE_IMPOSTOR:
                player.assign_tasks(num_tasks=random.randint(2, 4))
            else:
                player.tasks = [] 
            player.set_initial_alibi_and_current_state() 

        if not any(imp.is_alive for imp in self.impostors): # Check if any impostors are alive to make a move
            self.game_over = True # No living impostors, game should end (crew wins)
            self.fact_log.append("No living impostors to make a move.")
            return False # Indicates setup cannot proceed for a kill

        acting_impostor = random.choice([imp for imp in self.impostors if imp.is_alive])
        # No need to check 'if not acting_impostor' due to the check above

        possible_victims = self.get_alive_crewmates()
        if not possible_victims: # No crewmates left to kill
            self.game_over = True # Impostors should win or game ends
            self.fact_log.append("No crewmates left for the impostor to target.")
            return False # Setup cannot proceed for a kill
        
        self.victim = random.choice(possible_victims)
        self.victim.is_alive = False
        
        if random.random() < IMPOSTOR_LIE_QUALITY:
            possible_murder_rooms = {self.victim.current_location, acting_impostor.current_location}
            adj_to_victim = self._get_adjacent_rooms(self.victim.current_location)
            if adj_to_victim: possible_murder_rooms.add(random.choice(adj_to_victim))
            self.murder_room = random.choice(list(possible_murder_rooms))
        else:
            self.murder_room = random.choice(self.rooms)

        acting_impostor.alibi_location = self.murder_room
        acting_impostor.current_location = self.murder_room 
        fake_task = "looking suspicious"
        if self.location_tasks[self.murder_room]:
            fake_task = f"faking '{random.choice(self.location_tasks[self.murder_room])}'"
        acting_impostor.alibi_task = fake_task
        acting_impostor.current_task_description = fake_task

        self.fact_log.append(f"Victim: {self.victim.name} (was {self.victim.role}) has been found dead.")
        self.fact_log.append(f"Body discovered in: {self.murder_room}.")
        self.fact_log.append(f"{self.victim.name}'s last known true location: {self.victim.current_location} (supposedly doing '{self.victim.current_task_description}').")

        possible_reporters = [p for p in self.get_alive_players() if p != self.victim]
        self.reporter = random.choice(possible_reporters) if possible_reporters else acting_impostor 
        self.fact_log.append(f"Body reported by: {self.reporter.name}.")
        
        for player in self.players:
            if player != acting_impostor and player != self.victim: # Ensure alibis are current for others
                player.set_initial_alibi_and_current_state() 
        return True

    def _get_adjacent_rooms(self, room_name):
        adj = []
        if room_name not in self.rooms: return adj
        current_index = self.rooms.index(room_name)
        
        if current_index > 0: adj.append(self.rooms[current_index-1])
        if current_index < len(self.rooms) - 1 : adj.append(self.rooms[current_index+1])
        
        other_rooms = [r for r in self.rooms if r != room_name and r not in adj]
        if other_rooms and len(adj) < 2: adj.append(random.choice(other_rooms))
        return list(set(adj))


    def _generate_sightings(self):
        typewriter_print("\n--- Generating Sightings & Clues ---", 0.02)
        sighting_chance = SIGHTING_PROBABILITY
        if self.sabotage_active == "Lights Out":
            sighting_chance *= (1 - SABOTAGE_LIGHTS_OUT_SIGHTING_REDUCTION)
            self.fact_log.append("NOTE: Lights were out during the last period, making sightings less reliable!")

        for p_seer in self.get_alive_players():
            if p_seer == self.victim : continue 

            if random.random() < sighting_chance:
                possible_seen_targets = [p_other for p_other in self.players if p_other != p_seer] 
                if not possible_seen_targets: continue

                seen_person = None
                rand_roll = random.random()
                
                impostors_near_seer = [imp for imp in self.impostors if imp.is_alive and (imp.current_location == p_seer.current_location or imp.current_location == self.murder_room)]

                if impostors_near_seer and rand_roll < SIGHTING_IMPOSTOR_BIAS:
                    seen_person = random.choice(impostors_near_seer)
                elif rand_roll < SIGHTING_IMPOSTOR_BIAS + SIGHTING_VICTIM_BIAS and (self.victim.current_location == p_seer.current_location or self.murder_room == p_seer.current_location):
                    seen_person = self.victim 
                else:
                    other_options = [p for p in possible_seen_targets if p.is_alive and p not in self.impostors and p != self.victim]
                    if other_options: seen_person = random.choice(other_options)
                    elif [imp for imp in self.impostors if imp.is_alive and imp not in impostors_near_seer]:
                         seen_person = random.choice([imp for imp in self.impostors if imp.is_alive and imp not in impostors_near_seer])


                if seen_person:
                    sighting_location = seen_person.current_location 
                    if random.random() > 0.75: 
                        adj_rooms = self._get_adjacent_rooms(sighting_location)
                        if adj_rooms: sighting_location = random.choice(adj_rooms)
                    
                    sighting_time = random.choice(["recently", "a little while ago", "just before the body was found"])
                    
                    sighting_desc = f"{p_seer.name} claims they saw {seen_person.name}"
                    if seen_person == self.victim and not self.victim.is_alive: 
                        sighting_desc += f"'s body in {sighting_location}."
                    else: 
                         sighting_desc += f" in {sighting_location} {sighting_time}."
                    
                    self.round_sightings.append(sighting_desc)
                    self.fact_log.append(sighting_desc)
                    time.sleep(0.1)
        if not self.round_sightings:
            self.fact_log.append("No specific new sightings were reported this round.")
        print_separator("-", 30)


    def _perform_special_roles_actions(self):
        typewriter_print("\n--- Special Roles Taking Action (Privately) ---", 0.02)
        action_taken = False
        for player in self.get_alive_players():
            if player.role == ROLE_MEDIC:
                action_taken = True
                targets = [p for p in self.get_alive_players() if p != player and p != self.victim] 
                if targets:
                    scanned_player = random.choice(targets)
                    is_impostor_scan = scanned_player.role == ROLE_IMPOSTOR
                    
                    scan_result_text = "CLEAR (Not an Impostor)"
                    if is_impostor_scan:
                        scan_result_text = "SUSPICIOUS (Detected as Impostor!)"
                        if self.num_impostors > 1: 
                             scan_result_text = "HIGHLY SUSPICIOUS (Strong Impostor Reading!)"
                    
                    player.special_role_info = f"My Medic scan of {scanned_player.name} indicates they are: {scan_result_text}."
                    self.fact_log.append(f"Medic {player.name} performed a scan (results are private to them).")
                    time.sleep(0.2)

            elif player.role == ROLE_DETECTIVE:
                action_taken = True
                targets = [p for p in self.get_alive_players() if p != player and p != self.victim]
                if targets:
                    investigated_player = random.choice(targets)
                    is_actually_impostor = investigated_player.role == ROLE_IMPOSTOR
                    clue_is_correct_this_time = random.random() < DETECTIVE_CLUE_ACCURACY
                    
                    derived_clue_innocent = "seems innocent"
                    derived_clue_suspicious = "seems suspicious"

                    if clue_is_correct_this_time:
                        clue_text = derived_clue_suspicious if is_actually_impostor else derived_clue_innocent
                    else: 
                        clue_text = derived_clue_innocent if is_actually_impostor else derived_clue_suspicious
                    
                    player.special_role_info = f"My Detective instincts about {investigated_player.name}: they {clue_text}."
                    self.fact_log.append(f"Detective {player.name} followed a lead (clue is private to them).")
                    time.sleep(0.2)
        if action_taken:
            print_separator("-", 30)


    def _impostor_sabotage_attempt(self):
        if not any(imp.is_alive for imp in self.impostors): return

        acting_impostor = random.choice([imp for imp in self.impostors if imp.is_alive])
        if random.random() < SABOTAGE_CHANCE:
            available_sabotages = ["Lights Out"] 
            self.sabotage_active = random.choice(available_sabotages)
            
            if self.sabotage_active == "Lights Out":
                typewriter_print("\n🚨 SABOTAGE! The lights suddenly flicker and go out! 🚨", 0.04)
                self.fact_log.append("ALERT: An Impostor has sabotaged the Lights!")
            time.sleep(0.5)


    def _present_information_for_meeting(self):
        print_separator("+")
        typewriter_print("  Emergency Meeting! Discuss the findings!  ", 0.04)
        print_separator("+")
        time.sleep(0.5)

        typewriter_print("\n--- Official Report ---")
        print(f"The deceased: {self.victim.name} (was a {self.victim.role}).") 
        print(f"Body found by {self.reporter.name} in {self.murder_room}.")
        print(f"{self.victim.name}'s last verified location: {self.victim.current_location}, where they were supposedly {self.victim.current_task_description}.")
        time.sleep(0.5)

        typewriter_print("\n--- Player Alibis & Statements ---")
        sorted_living_players = sorted(self.get_alive_players(), key=lambda p: p.name)

        for player in sorted_living_players:
            statement = f"- {player.name}: \"I was in {player.alibi_location} working on '{player.alibi_task}'.\""
            if player.special_role_info: 
                if player.role == ROLE_MEDIC and ("SUSPICIOUS" in player.special_role_info or "Impostor" in player.special_role_info) and random.random() < 0.7:
                    statement += f" Also, {player.special_role_info}"
                elif player.role == ROLE_DETECTIVE and "suspicious" in player.special_role_info and random.random() < 0.6:
                     statement += f" Furthermore, {player.special_role_info}"
                elif player.role in [ROLE_MEDIC, ROLE_DETECTIVE] and random.random() < 0.25: 
                    statement += f" ({player.role}) My findings were: {player.special_role_info}"


            typewriter_print(statement)
            time.sleep(0.2)

        typewriter_print("\n--- Consolidated Fact Log & Observations This Round ---")
        round_specific_facts = [f for f in self.fact_log if "Round Start" not in f and "scan" not in f and "clue" not in f and "claims they saw" not in f] 
        round_specific_facts += self.round_sightings 

        # Check if there's meaningful new info beyond the boilerplate
        meaningful_new_info = False
        for fact in round_specific_facts:
            # These are considered boilerplate for this check
            if "Body discovered" in fact or "Reported by" in fact or "Victim:" in fact or "last known true location" in fact or "ALERT" in fact:
                continue
            if "No specific new sightings" in fact and len(self.round_sightings) == 0 : # if this is the only "new" fact
                continue

            meaningful_new_info = True # Any other fact (like a real sighting) is meaningful
            break
        
        if not meaningful_new_info and not self.round_sightings : # if no sightings and no other facts
             print("No new specific observations or sightings beyond the initial report and alibis.")
        
        for fact in round_specific_facts: # Print all gathered facts including sightings
            typewriter_print(f"* {fact}")
            time.sleep(0.15)
        
        if self.sabotage_active:
             typewriter_print(f"\nREMEMBER: {self.sabotage_active} sabotage occurred recently!", 0.04)

    def _get_player_vote(self, human_player_name=None): 
        print_separator("VOTE")
        alive_for_voting = [p for p in self.get_alive_players() if p != self.victim] 
        if not alive_for_voting: return None 

        ai_votes = {} 
        for voter in alive_for_voting:
            if voter.name == human_player_name: continue 

            possible_targets = [p_target for p_target in alive_for_voting if p_target != voter]
            if not possible_targets: continue

            chosen_vote_name = None
            if voter.role == ROLE_IMPOSTOR: 
                crew_targets = [t for t in possible_targets if t.role != ROLE_IMPOSTOR]
                if crew_targets: chosen_vote_name = random.choice(crew_targets).name
                else: chosen_vote_name = random.choice(possible_targets).name 
            elif (voter.role == ROLE_DETECTIVE or voter.role == ROLE_MEDIC) and voter.special_role_info:
                if ("SUSPICIOUS" in voter.special_role_info or "Impostor" in voter.special_role_info or "suspicious" in voter.special_role_info):
                    try: 
                        parts = voter.special_role_info.split("of ") if "of " in voter.special_role_info else voter.special_role_info.split("about ")
                        target_name_dirty = parts[1].split(" indicates")[0].split(" suggests")[0].split(":")[0].strip()
                        target_player = self.get_player_by_name(target_name_dirty)
                        if target_player and target_player.name in [t.name for t in possible_targets]:
                            if random.random() < 0.8: 
                                chosen_vote_name = target_player.name
                    except IndexError: pass 

            if not chosen_vote_name: 
                if random.random() < CREWMATE_ACCUSATION_ACCURACY and any(imp.is_alive for imp in self.impostors):
                    living_impostors = [imp for imp in self.impostors if imp.is_alive and imp in possible_targets]
                    if living_impostors: chosen_vote_name = random.choice(living_impostors).name
                if not chosen_vote_name: 
                     chosen_vote_name = random.choice(possible_targets).name
            
            ai_votes[voter.name] = chosen_vote_name
            typewriter_print(f"{voter.name} has cast their vote.", 0.01)
            time.sleep(0.05)

        human_voted_for_name = None
        if human_player_name and self.get_player_by_name(human_player_name) in alive_for_voting:
            while True:
                print_separator("~", 30)
                typewriter_print(f"It's your turn to vote, {human_player_name}!")
                votable_display = ", ".join(sorted([p.name for p in alive_for_voting]))
                print(f"(Players you can vote for: {votable_display})")
                guess_input = input("Enter color name of who you vote to eject: ").strip().title()
                
                voted_player_obj = self.get_player_by_name(guess_input)
                if voted_player_obj and voted_player_obj in alive_for_voting:
                    human_voted_for_name = voted_player_obj.name
                    ai_votes[human_player_name] = human_voted_for_name 
                    print(f"DEBUG: Human '{human_player_name}' voted for '{human_voted_for_name}'.") # DEBUG
                    break
                else:
                    typewriter_print(f"'{guess_input}' is not a valid or living player on the list. Try again.")
        
        print(f"DEBUG: ai_votes dictionary before tally: {ai_votes}") # DEBUG VOTE DICTIONARY

        vote_counts = {name: 0 for name in [p.name for p in alive_for_voting]}
        print(f"DEBUG: Initial vote_counts: {vote_counts}") # DEBUG INITIAL COUNTS
        for voter, voted_for in ai_votes.items():
            if voted_for in vote_counts: 
                print(f"DEBUG: Tallying vote from '{voter}' FOR '{voted_for}'. Current count for '{voted_for}' was {vote_counts[voted_for]}. ", end="") # DEBUG
                vote_counts[voted_for] += 1
                print(f"New count is {vote_counts[voted_for]}.") # DEBUG
            else:
                print(f"DEBUG WARNING: Player '{voted_for}' (voted by '{voter}') not in current vote_counts keys: {list(vote_counts.keys())}")


        typewriter_print("\n--- Vote Tally ---")
        if not vote_counts:
            typewriter_print("No votes were cast.")
            return None

        for name, count in sorted(vote_counts.items(), key=lambda item: item[1], reverse=True):
            print(f"{name}: {count} vote(s)")
        
        max_votes = max(vote_counts.values()) if vote_counts else 0
        voted_out_candidates = [name for name, count in vote_counts.items() if count == max_votes]

        if len(voted_out_candidates) == 1:
            return self.get_player_by_name(voted_out_candidates[0])
        elif len(voted_out_candidates) > 1: 
            typewriter_print("\nIt's a TIE! No one is ejected this round. The suspicion lingers...", 0.02)
            self.fact_log.append("The vote resulted in a tie. No one was ejected.")
            return None
        else: 
            typewriter_print("\nNo clear majority. No one is ejected.", 0.02)
            self.fact_log.append("No majority vote. No one was ejected.")
            return None

    def _check_win_conditions(self):
        alive_impostors = [p for p in self.impostors if p.is_alive]
        alive_crew = self.get_alive_crewmates() 

        if not alive_impostors:
            typewriter_print("\n🎉 ALL IMPOSTORS HAVE BEEN EJECTED! 🎉", 0.04)
            typewriter_print("✨ CREWMATES WIN! ✨", 0.04)
            self.game_over = True
            return True
        
        if len(alive_impostors) >= len(alive_crew):
            typewriter_print("\n☠️ THE IMPOSTORS HAVE OVERWHELMED THE CREW! ☠️", 0.04)
            typewriter_print("💔 IMPOSTORS WIN! 💔", 0.04)
            self.game_over = True
            return True
            
        return False

    def play_round(self):
        # _setup_round now returns False if game should end (e.g. no victims, no impostors)
        if not self._setup_round(): 
             # If setup indicates game should end (e.g. win condition met during setup)
             if not self.game_over: # If game_over wasn't set by _setup_round explicitly
                 typewriter_print("Game cannot proceed with round setup (e.g. no valid victims or impostors). Checking win conditions...", 0.02)
                 self._check_win_conditions() # Ensure game_over is set if a win condition is met
             return # End play_round early

        self._impostor_sabotage_attempt() 
        self._generate_sightings()
        self._perform_special_roles_actions()

        self._present_information_for_meeting()
        
        human_player = self.players[0] if self.players else None 
        
        ejected_player = self._get_player_vote(human_player_name=human_player.name if human_player else None)

        print_separator("OUTCOME")
        if ejected_player:
            ejected_player.is_alive = False 
            typewriter_print(f"\n...{ejected_player.name} was ejected...", 0.05)
            time.sleep(1)
            was_impostor = ejected_player.role == ROLE_IMPOSTOR
            typewriter_print(f"{ejected_player.name} was {'' if was_impostor else 'NOT '}an Impostor. Their role was: {ejected_player.role}.", 0.04)
            time.sleep(1.5)
        else:
            typewriter_print("No one was ejected. The game continues with heightened suspicion...", 0.02)
            time.sleep(1.5)
        
        self._check_win_conditions() # This is the primary place game_over is set after a round's actions


    def start_game(self):
        print_separator("=", 60)
        typewriter_print("  WELCOME TO THE ADVANCED 'FIND THE IMPOSTOR' GAME!  ", 0.04)
        print_separator("=", 60)
        time.sleep(0.5)

        self._assign_roles() 
        
        round_num = 0
        while not self.game_over:
            # DEBUG: print(f"DEBUG: Start of while in start_game. Round: {round_num+1}. self.game_over: {self.game_over}")
            round_num += 1
            print_separator("*")
            typewriter_print(f"Starting Round {round_num}...", 0.03)
            time.sleep(0.5)
            
            self.play_round() 
            
            if self.game_over: # Check if play_round resulted in game over
                # Final revelation printed here
                typewriter_print("\n--- FINAL GAME REVELATION ---", 0.03)
                for p_obj in self.players: 
                    status = "Survived" if p_obj.is_alive else "Deceased"
                    if p_obj.role == ROLE_IMPOSTOR: # More specific status for impostors
                        status = "Escaped!" if p_obj.is_alive else "Caught"
                    elif not p_obj.is_alive : # For non-impostors who are dead
                        status = "Killed or Ejected"
                    print(f"{p_obj.name}: Role - {p_obj.role}, Status - {status}")
                break # Exit the while loop
            
            # Stalemate check only if game not already over
            if round_num > self.num_players * 2 + 2 : # Slightly increased threshold for stalemate
                typewriter_print("The investigation has dragged on for too long, becoming a stalemate.", 0.03)
                remaining_impostors_obj = [imp for imp in self.impostors if imp.is_alive]
                if remaining_impostors_obj:
                    print(f"The remaining impostor(s) ({', '.join([imp.name for imp in remaining_impostors_obj])}) managed to evade justice. Impostors win by default.")
                else: 
                    print("Stalemate, but all impostors were eliminated. A strange victory for the Crew.")
                self.game_over = True
                break # ADDED EXPLICIT BREAK HERE for stalemate


# --- Main Game Execution ---
if __name__ == "__main__":
    while True:
        try:
            print_separator("#", 60)
            num_total_players_str = input(f"Enter number of players ({MIN_PLAYERS}-{MAX_PLAYERS}): ")
            if not num_total_players_str.isdigit():
                print("Invalid input. Please enter a number.")
                continue
            num_total_players = int(num_total_players_str)

            if not (MIN_PLAYERS <= num_total_players <= MAX_PLAYERS):
                print(f"Please enter a number of players between {MIN_PLAYERS} and {MAX_PLAYERS}.")
                continue
            
            max_allowed_impostors = 1
            if num_total_players >= 7:
                max_allowed_impostors = 2
            elif num_total_players >= 5: 
                max_allowed_impostors = min(2, (num_total_players-1)//2) if (num_total_players-1)//2 >=1 else 1


            num_imps = 1 
            if num_total_players >= 5 and max_allowed_impostors > 1: 
                num_imps_str = input(f"Enter number of impostors (1-{max_allowed_impostors}, default 1): ")
                if num_imps_str.isdigit():
                    temp_num_imps = int(num_imps_str)
                    if 1 <= temp_num_imps <= max_allowed_impostors:
                        num_imps = temp_num_imps
                    else:
                        print(f"Invalid number of impostors. Defaulting to 1.")
                else:
                    print("Invalid input for impostor count. Defaulting to 1.")
            
            game_instance = Game(num_players=num_total_players, num_impostors=num_imps)
            game_instance.start_game()

        except ValueError:
            print("Invalid input type. Please ensure you enter numbers where expected.")
        except Exception as e:
            typewriter_print(f"\nAn unexpected critical error occurred: {e}", 0.02)
            import traceback
            traceback.print_exc() 

        print_separator()
        again = input("Play again? (yes/no): ").strip().lower()
        if again not in ['yes', 'y']:
            typewriter_print("\nThanks for playing the advanced game! Goodbye!", 0.03)
            break
