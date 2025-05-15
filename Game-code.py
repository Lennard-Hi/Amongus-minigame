import random
import time

# --- Constants ---
ALL_PLAYERS_COLORS = ["Red", "Blue", "Green", "Yellow", "Pink", "Orange", "Black", "White", "Purple", "Cyan"]
MIN_PLAYERS = 5 # Minimum players needed for a game

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
SIGHTING_PROBABILITY = 0.5  # Chance a player sees someone
SIGHTING_IMPOSTOR_BIAS = 0.4 # If a sighting occurs, chance it's an impostor
SIGHTING_VICTIM_BIAS = 0.3 # If a sighting occurs (and not impostor), chance it's the victim
MEDIC_SCAN_ACCURACY = 1.0 # Medic is always correct
DETECTIVE_CLUE_ACCURACY = 0.85 # Detective's clue is mostly reliable
IMPOSTOR_LIE_QUALITY = 0.7 # How good impostors are at picking believable fake tasks
CREWMATE_ACCUSATION_ACCURACY = 0.3 # How often a crewmate's random suspicion is correct
SABOTAGE_LIGHTS_OUT_SIGHTING_REDUCTION = 0.5 # Reduces sighting probability

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
        self.completed_tasks = 0
        self.current_location = None
        self.current_task_description = "wandering"
        self.alibi_location = None
        self.alibi_task = "no specific task"
        self.special_role_info = "" # For Medic scan, Detective clue

    def assign_tasks(self, num_tasks=3):
        self.tasks = []
        available_locations = list(self.game.location_tasks.keys())
        for _ in range(num_tasks):
            if not available_locations: break
            loc = random.choice(available_locations)
            if self.game.location_tasks[loc]:
                task = random.choice(self.game.location_tasks[loc])
                self.tasks.append({"location": loc, "task": task, "completed": False})
            # A location might have no tasks if all picked, or few tasks.
            # To simplify, we don't strictly prevent duplicate task types in different locations here.

    def set_initial_location_and_task_for_alibi(self):
        if self.tasks:
            # Try to pick an incomplete task for initial location
            incomplete_tasks = [t for t in self.tasks if not t['completed']]
            if incomplete_tasks:
                chosen_task_info = random.choice(incomplete_tasks)
                self.current_location = chosen_task_info['location']
                self.current_task_description = chosen_task_info['task']
            else: # All tasks done, or no tasks assigned (e.g. impostor)
                self.current_location = random.choice(self.game.rooms)
                self.current_task_description = random.choice(self.game.location_tasks[self.current_location]) if self.game.location_tasks[self.current_location] else "observing"
        else: # Impostor or special case
            self.current_location = random.choice(self.game.rooms)
            self.current_task_description = random.choice(self.game.location_tasks[self.current_location]) if self.game.location_tasks[self.current_location] else "looking busy"

        self.alibi_location = self.current_location
        self.alibi_task = self.current_task_description


    def __str__(self):
        return f"{self.name} ({self.role if self.game.game_over else 'Unknown'})"

class Game:
    def __init__(self, num_players=7, num_impostors=1):
        self.num_players = max(MIN_PLAYERS, num_players)
        self.num_impostors = num_impostors if num_impostors < num_players // 2 else 1
        self.players = [Player(name, self) for name in random.sample(ALL_PLAYERS_COLORS, self.num_players)]
        self.location_tasks = LOCATION_TASKS
        self.rooms = ROOMS
        self.impostors = []
        self.victim = None
        self.reporter = None
        self.murder_room = None
        self.fact_log = []
        self.game_over = False
        self.sabotage_active = None # e.g., "Lights Out"
        self.round_sightings = []

    def get_player_by_name(self, name):
        for player in self.players:
            if player.name == name:
                return player
        return None

    def get_alive_players(self):
        return [p for p in self.players if p.is_alive]

    def get_alive_crewmates(self):
        return [p for p in self.get_alive_players() if p.role != ROLE_IMPOSTOR]

    def _assign_roles(self):
        print_separator("-")
        typewriter_print("Assigning roles secretly...")
        time.sleep(1)
        
        available_players = list(self.players)
        random.shuffle(available_players)

        # Assign Impostors
        for _ in range(self.num_impostors):
            if available_players:
                impostor_player = available_players.pop()
                impostor_player.role = ROLE_IMPOSTOR
                self.impostors.append(impostor_player)

        # Assign Special Crewmate Roles
        crew_for_special_roles = [p for p in available_players if p.role == ROLE_CREWMATE]
        random.shuffle(crew_for_special_roles)

        if crew_for_special_roles:
            medic_player = crew_for_special_roles.pop()
            medic_player.role = ROLE_MEDIC
        if crew_for_special_roles: # if enough players left
            detective_player = crew_for_special_roles.pop()
            detective_player.role = ROLE_DETECTIVE
        
        print("Roles assigned.")
        if self.num_impostors > 1:
            typewriter_print(f"There are {self.num_impostors} impostors among us.")
        else:
            typewriter_print("There is 1 impostor among us.")


    def _setup_round(self):
        self.game_over = False
        self.fact_log = []
        self.round_sightings = []
        self.sabotage_active = None

        # Assign tasks to all players (impostors don't 'do' tasks but need alibis)
        for player in self.players:
            player.is_alive = True # Revive all for new game
            if player.role != ROLE_IMPOSTOR:
                player.assign_tasks(num_tasks=random.randint(2,4))
            else:
                player.tasks = [] # Impostors don't have real tasks
            player.set_initial_location_and_task_for_alibi()


        # Impostor chooses victim and location
        if not self.impostors: # Should not happen if roles assigned
            print("Error: No impostors assigned!")
            return False 

        primary_impostor = random.choice(self.impostors) # In case of multiple impostors, one takes lead for the kill
        
        possible_victims = [p for p in self.players if p.role != ROLE_IMPOSTOR and p.is_alive]
        if not possible_victims:
            print("Error: No possible victims!") # Should not happen in a normal game start
            return False
        self.victim = random.choice(possible_victims)
        self.victim.is_alive = False
        
        # Impostor's fake location choice
        if random.random() < IMPOSTOR_LIE_QUALITY: # Impostor tries to be smart
            # Options: victim's last known real location, adjacent room, or a busy room
            possible_murder_rooms = [self.victim.current_location] + self._get_adjacent_rooms(self.victim.current_location)
            self.murder_room = random.choice(list(set(possible_murder_rooms))) # Use set to avoid duplicates
            if not self.murder_room : self.murder_room = random.choice(self.rooms) # Fallback
        else: # Impostor picks a random room
            self.murder_room = random.choice(self.rooms)

        primary_impostor.alibi_location = self.murder_room # Impostor was "at the scene"
        primary_impostor.alibi_task = f"faking '{random.choice(self.location_tasks[self.murder_room]) if self.location_tasks[self.murder_room] else 'something'}'"
        primary_impostor.current_location = self.murder_room # For sighting purposes too

        # Victim's actual location and task before death
        self.victim.alibi_location = self.victim.current_location # Where they actually were
        self.victim.alibi_task = self.victim.current_task_description

        self.fact_log.append(f"Victim: {self.victim.name} was found dead.")
        self.fact_log.append(f"Body found in: {self.murder_room}.")
        self.fact_log.append(f"{self.victim.name}'s last known actual location before death: {self.victim.alibi_location} (doing '{self.victim.alibi_task}').")


        # Reporter
        possible_reporters = [p for p in self.get_alive_players() if p != self.victim and p not in self.impostors]
        if not possible_reporters: # Impostor might self-report
            possible_reporters = [p for p in self.get_alive_players() if p != self.victim]

        self.reporter = random.choice(possible_reporters) if possible_reporters else primary_impostor
        self.fact_log.append(f"Reported by: {self.reporter.name}.")
        
        # All other players set their alibis (they were somewhere doing something)
        for player in self.players:
            if player != primary_impostor and player != self.victim: # Impostor and victim alibis are special
                player.set_initial_location_and_task_for_alibi() # Re-set for those not involved in murder scene
        return True

    def _get_adjacent_rooms(self, room_name):
        # This is a simplified adjacency, real maps are more complex.
        # For now, just return a couple of random other rooms.
        adj = []
        current_index = self.rooms.index(room_name) if room_name in self.rooms else -1
        if current_index != -1:
            if current_index > 0: adj.append(self.rooms[current_index-1])
            if current_index < len(self.rooms) -1 : adj.append(self.rooms[current_index+1])
        # Add one more random non-adjacent for variety if possible
        other_rooms = [r for r in self.rooms if r != room_name and r not in adj]
        if other_rooms: adj.append(random.choice(other_rooms))
        return list(set(adj))[:2] # Max 2 adjacent for simplicity

    def _generate_sightings(self):
        typewriter_print("\n--- Generating Sightings & Clues ---")
        sighting_chance = SIGHTING_PROBABILITY
        if self.sabotage_active == "Lights Out":
            sighting_chance *= (1 - SABOTAGE_LIGHTS_OUT_SIGHTING_REDUCTION)
            self.fact_log.append("NOTE: Lights were out, making sightings harder!")

        for p_seer in self.get_alive_players():
            if p_seer == self.victim: continue

            if random.random() < sighting_chance:
                # Who was seen?
                possible_seen = [p_other for p_other in self.players if p_other != p_seer] # Can see dead bodies too
                if not possible_seen: continue

                seen_person = None
                rand_roll = random.random()

                # Bias towards seeing impostors or victim
                impostors_at_scene = [imp for imp in self.impostors if imp.current_location == p_seer.current_location or imp.current_location == self.murder_room]

                if impostors_at_scene and rand_roll < SIGHTING_IMPOSTOR_BIAS:
                    seen_person = random.choice(impostors_at_scene)
                elif self.victim.current_location == p_seer.current_location and rand_roll < SIGHTING_IMPOSTOR_BIAS + SIGHTING_VICTIM_BIAS : #and not seen_person yet
                     seen_person = self.victim # Player might have seen victim before death or the body
                else: # See another random player
                    other_options = [p for p in possible_seen if p not in self.impostors and p != self.victim]
                    if other_options:
                        seen_person = random.choice(other_options)
                    elif [imp for imp in self.impostors if imp not in impostors_at_scene]: # see other impostors not at scene
                        seen_person = random.choice([imp for imp in self.impostors if imp not in impostors_at_scene])


                if seen_person:
                    # Where was the person seen? Usually their current/alibi location.
                    # Add some noise: 70% chance it's their actual location, 30% an adjacent one
                    sighting_location = seen_person.alibi_location # Their claimed spot
                    if random.random() > 0.7:
                        adj_rooms = self._get_adjacent_rooms(sighting_location)
                        if adj_rooms : sighting_location = random.choice(adj_rooms)

                    sighting_time = random.choice(["recently", "a little while ago", "just before the report"])
                    
                    sighting_detail = f"{p_seer.name} saw {seen_person.name} in {sighting_location} {sighting_time}."
                    if seen_person == self.victim and not seen_person.is_alive :
                         sighting_detail = f"{p_seer.name} saw {seen_person.name}'s body in {sighting_location}."
                    elif seen_person == self.victim and seen_person.is_alive : # Victim seen alive
                         sighting_detail = f"{p_seer.name} saw {seen_person.name} (alive) in {sighting_location} {sighting_time}."

                    self.round_sightings.append(sighting_detail)
                    self.fact_log.append(sighting_detail)
                    time.sleep(0.2)
        if not self.round_sightings:
            self.fact_log.append("No specific sightings reported this round.")


    def _perform_special_roles_actions(self):
        typewriter_print("\n--- Special Roles Taking Action ---")
        time.sleep(0.5)
        for player in self.get_alive_players():
            if player.role == ROLE_MEDIC:
                targets = [p for p in self.get_alive_players() if p != player and p != self.victim]
                if targets:
                    scanned_player = random.choice(targets)
                    is_clear = scanned_player.role != ROLE_IMPOSTOR
                    scan_result = "clear" if is_clear else "suspicious (Impostor!)" # Medic always accurate
                    if self.game.num_impostors > 1 and not is_clear: # Don't reveal if multiple impostors unless game settings change
                        scan_result = "inconclusive due to interference" # Nerf for multiple impostors
                    
                    player.special_role_info = f"As Medic, I scanned {scanned_player.name}. They are {scan_result}."
                    self.fact_log.append(f"Medic {player.name} performed a scan.") # Don't reveal result to everyone, only medic knows.
                    time.sleep(0.3)

            elif player.role == ROLE_DETECTIVE:
                targets = [p for p in self.get_alive_players() if p != player and p != self.victim]
                if targets:
                    investigated_player = random.choice(targets)
                    actually_impostor = investigated_player.role == ROLE_IMPOSTOR
                    clue_is_correct = random.random() < DETECTIVE_CLUE_ACCURACY
                    
                    if clue_is_correct:
                        clue = "seems suspicious" if actually_impostor else "seems innocent"
                    else: # Misleading clue
                        clue = "seems innocent" if actually_impostor else "seems suspicious"
                    
                    player.special_role_info = f"As Detective, my investigation of {investigated_player.name} suggests they {clue}."
                    self.fact_log.append(f"Detective {player.name} found a clue.") # Don't reveal to everyone
                    time.sleep(0.3)
        print_separator("-", 30)


    def _impostor_sabotage_attempt(self):
        if not self.impostors: return
        # For now, only one impostor can sabotage per round if multiple impostors
        acting_impostor = random.choice(self.impostors)
        if acting_impostor.is_alive and random.random() < 0.33: # 33% chance for sabotage
            available_sabotages = ["Lights Out", "Comms Down"] # Comms not implemented yet
            self.sabotage_active = random.choice(available_sabotages)
            if self.sabotage_active == "Lights Out":
                typewriter_print("\n🚨 SABOTAGE! The lights suddenly go out! 🚨", 0.05)
                self.fact_log.append("ALERT: Impostor sabotaged the Lights!")
            # elif self.sabotage_active == "Comms Down":
            #     typewriter_print("\n🚨 SABOTAGE! Communications are down! 🚨", 0.05)
            #     self.fact_log.append("ALERT: Impostor sabotaged Comms! (Effect: Some info might be hidden)")
            time.sleep(1)


    def _present_information(self):
        print_separator("+")
        typewriter_print("  Emergency Meeting Called!  ", 0.05)
        print_separator("+")
        time.sleep(1)

        typewriter_print("\n--- Victim Information ---")
        print(f"The deceased is {self.victim.name}.")
        print(f"Body found by {self.reporter.name} in {self.murder_room}.")
        print(f"{self.victim.name} was last seen alive in {self.victim.alibi_location} supposedly {self.victim.alibi_task}.")
        time.sleep(0.5)

        typewriter_print("\n--- Player Alibis (What they CLAIM) ---")
        # Sort players for consistent output, maybe by color name or keep random for chaos
        sorted_living_players = sorted(self.get_alive_players(), key=lambda p: p.name)

        for player in sorted_living_players:
            role_display = ""
            if player.role == ROLE_MEDIC and player.special_role_info: role_display = f" ({player.role} - {player.special_role_info})"
            elif player.role == ROLE_DETECTIVE and player.special_role_info: role_display = f" ({player.role} - {player.special_role_info})"
            elif player.role in [ROLE_MEDIC, ROLE_DETECTIVE]: role_display = f" ({player.role})"
            
            typewriter_print(f"- {player.name}{role_display}: \"I was in {player.alibi_location} doing '{player.alibi_task}'.\"")
            time.sleep(0.3)

        typewriter_print("\n--- Consolidated Fact Log & Observations ---")
        if not self.fact_log:
            print("No specific facts gathered beyond initial report.")
        for fact in self.fact_log:
            if "saw" in fact or "No specific sightings" in fact or "ALERT" in fact or "scan" in fact or "clue" in fact : # Filter for more dynamic facts
                typewriter_print(f"* {fact}")
                time.sleep(0.2)
        
        if self.sabotage_active:
             typewriter_print(f"\nREMEMBER: {self.sabotage_active} sabotage is active!", 0.05)


    def _get_player_vote(self, human_player_name="Blue"): # Assume human is 'Blue' or let them choose
        print_separator("VOTE")
        alive_for_voting = [p for p in self.get_alive_players() if p != self.victim]
        
        # AI Votes (Simple)
        ai_votes = {}
        for player in alive_for_voting:
            if player.name == human_player_name and self.num_players > 1 : continue # Skip human player's AI vote if human is playing

            possible_targets = [p_target for p_target in alive_for_voting if p_target != player]
            if not possible_targets: continue

            # AI Logic:
            # 1. If Detective/Medic has strong suspicion, they might vote for it.
            # 2. Impostors try to vote for a non-impostor, or someone accusing them.
            # 3. Crewmates might get influenced by accusations or detective.
            # For now, simplified:
            chosen_vote = None
            if player.role == ROLE_IMPOSTOR:
                # Try to vote for a crewmate, ideally one who seems suspicious or a Detective/Medic
                crew_targets = [t for t in possible_targets if t.role != ROLE_IMPOSTOR]
                if crew_targets: chosen_vote = random.choice(crew_targets).name
                else: chosen_vote = random.choice(possible_targets).name # fallback
            elif player.role == ROLE_DETECTIVE and player.special_role_info and "suspicious" in player.special_role_info:
                # Detective might vote based on their clue
                try:
                    target_name = player.special_role_info.split("of ")[1].split(" suggests")[0]
                    if self.get_player_by_name(target_name) in possible_targets:
                        if random.random() < 0.7: # High chance to follow own clue
                             chosen_vote = target_name
                except: pass # Parsing error
            
            if not chosen_vote: # Default random vote
                if random.random() < CREWMATE_ACCUSATION_ACCURACY and self.impostors: # Small chance to correctly guess impostor
                    chosen_vote = random.choice(self.impostors).name
                    if self.get_player_by_name(chosen_vote) not in possible_targets : chosen_vote = None # if impostor is not votable
                if not chosen_vote :
                    chosen_vote = random.choice(possible_targets).name
            
            ai_votes[player.name] = chosen_vote
            typewriter_print(f"{player.name} has voted.", 0.01) # Keep AI votes quick
            time.sleep(0.1)

        # Human Player Vote
        if self.num_players == 1 and self.get_player_by_name(human_player_name) not in alive_for_voting: # Single player mode, human is the only voter effectively
            human_player_name = alive_for_voting[0].name # Auto-assign if in SP mode.

        if self.get_player_by_name(human_player_name) in alive_for_voting or self.num_players == 0: # num_players == 0 implies a fully AI game
            while True:
                print_separator("~", 30)
                typewriter_print(f"Who do YOU ({human_player_name if self.num_players > 0 else 'Observer'}) vote as the Impostor?")
                votable_display = ", ".join([p.name for p in alive_for_voting])
                print(f"(Available to vote for: {votable_display})")
                if self.num_players == 0 : # Fully AI game
                    time.sleep(2) # Pause for observer
                    # In fully AI, just tally votes without human input
                    break

                guess_input = input("Enter color name: ").strip().title()
                if self.get_player_by_name(guess_input) in alive_for_voting:
                    ai_votes[human_player_name] = guess_input # Add human vote
                    break
                else:
                    typewriter_print(f"'{guess_input}' is not a valid or living player. Please choose from the list.")
        
        # Tally Votes
        vote_counts = {name: 0 for name in [p.name for p in alive_for_voting]}
        for voter, voted_for in ai_votes.items():
            if voted_for in vote_counts:
                vote_counts[voted_for] += 1
        
        typewriter_print("\n--- Vote Tally ---")
        for name, count in sorted(vote_counts.items(), key=lambda item: item[1], reverse=True):
            print(f"{name}: {count} vote(s)")
        
        max_votes = 0
        voted_out_players = []
        if vote_counts : # Check if vote_counts is not empty
            max_votes = max(vote_counts.values())
            voted_out_players = [name for name, count in vote_counts.items() if count == max_votes]

        if len(voted_out_players) == 1:
            return self.get_player_by_name(voted_out_players[0])
        elif len(voted_out_players) > 1:
            typewriter_print("\nIt's a TIE! No one is ejected. The tension rises...")
            self.fact_log.append("Vote was a tie. No one ejected.")
            return None # Tie, no one ejected
        else: # No votes or error
            typewriter_print("\nNo majority vote. No one is ejected.")
            self.fact_log.append("No majority vote. No one ejected.")
            return None


    def _check_win_conditions(self):
        alive_impostors = [p for p in self.impostors if p.is_alive]
        alive_crewmates = self.get_alive_crewmates()

        if not alive_impostors:
            typewriter_print("\n🎉 ALL IMPOSTORS EJECTED/NEUTRALIZED! 🎉", 0.05)
            typewriter_print("✨ CREWMATES WIN! ✨", 0.05)
            self.game_over = True
            return True
        
        if len(alive_impostors) >= len(alive_crewmates):
            typewriter_print("\n☠️ IMPOSTORS HAVE OVERTAKEN THE CREW! ☠️", 0.05)
            typewriter_print("💔 IMPOSTORS WIN! 💔", 0.05)
            self.game_over = True
            return True
        
        # Optional: Task win condition for crewmates (not fully implemented with task tracking yet)
        # total_tasks = sum(len(p.tasks) for p in self.players if p.role != ROLE_IMPOSTOR)
        # completed_tasks = sum(p.completed_tasks for p in self.players if p.role != ROLE_IMPOSTOR)
        # if total_tasks > 0 and completed_tasks >= total_tasks:
        #     print("\n🎉 ALL TASKS COMPLETED! 🎉")
        #     print("✨ CREWMATES WIN! ✨")
        #     self.game_over = True
        #     return True
            
        return False

    def play_round(self):
        if not self._setup_round():
             typewriter_print("Failed to set up the round. Game cannot continue.", 0.05)
             self.game_over = True
             return

        self._impostor_sabotage_attempt() # Impostor might sabotage before meeting
        self._generate_sightings()
        self._perform_special_roles_actions() # Medic/Detective gather info

        self._present_information()
        
        ejected_player = self._get_player_vote()

        print_separator("OUTCOME")
        if ejected_player:
            ejected_player.is_alive = False
            typewriter_print(f"\n{ejected_player.name} was ejected.")
            time.sleep(1)
            if ejected_player.role == ROLE_IMPOSTOR:
                typewriter_print(f"{ejected_player.name} WAS an Impostor!", 0.05)
                # Remove from active impostors list
                if ejected_player in self.impostors: self.impostors.remove(ejected_player) # careful with modifying list during iteration if it happens
            else:
                typewriter_print(f"{ejected_player.name} was NOT an Impostor. They were a {ejected_player.role}.", 0.05)
            time.sleep(1.5)
        else:
            typewriter_print("No one was ejected. The game continues...", 0.05)
            time.sleep(1.5)
        
        self._check_win_conditions()


    def start_game(self):
        print_separator("=", 60)
        typewriter_print("  WELCOME TO THE ADVANCED 'FIND THE IMPOSTOR' GAME!  ", 0.05)
        print_separator("=", 60)
        time.sleep(1)

        self._assign_roles()
        
        round_num = 0
        while not self.game_over:
            round_num += 1
            print_separator("*")
            typewriter_print(f"Starting Round {round_num}...")
            print_separator("*")
            time.sleep(1)
            self.play_round()
            
            if self.game_over:
                typewriter_print("\n--- FINAL REVEAL ---")
                for player in self.players: # Show all original roles
                    role_info = player.role
                    if player in self.impostors and player.is_alive : role_info += " (Escaped)"
                    elif player in self.impostors and not player.is_alive : role_info += " (Caught)"

                    print(f"{player.name} was {role_info}")
                break
            
            # Check for stale game (e.g. if no one can be voted out and no win)
            if round_num > self.num_players * 2 : # Heuristic for too many rounds
                typewriter_print("The situation is a stalemate. Impostors vanish into the shadows...", 0.05)
                # Could declare impostor win or draw here.
                impostor_names = [imp.name for imp in self.impostors if imp.is_alive]
                if impostor_names:
                    print(f"The remaining impostor(s) {', '.join(impostor_names)} win by default.")
                else: # Should be caught by win condition
                    print("Stalemate. No clear winner.")
                self.game_over = True


# --- Main Game Loop ---
if __name__ == "__main__":
    while True:
        try:
            num_total_players = int(input(f"Enter number of players ({MIN_PLAYERS}-{len(ALL_PLAYERS_COLORS)}): "))
            if not MIN_PLAYERS <= num_total_players <= len(ALL_PLAYERS_COLORS):
                print(f"Please enter a number between {MIN_PLAYERS} and {len(ALL_PLAYERS_COLORS)}.")
                continue
            
            max_impostors = (num_total_players -1) // 2 
            if max_impostors < 1: max_impostors = 1
            
            num_imps = 1 # Default
            if num_total_players > 5: # Allow choosing num impostors for more players
                num_imps_str = input(f"Enter number of impostors (1-{max_impostors}, default 1): ")
                if num_imps_str.isdigit():
                    num_imps = int(num_imps_str)
                    if not (1 <= num_imps <= max_impostors) :
                        num_imps = 1
                        print(f"Invalid number of impostors, defaulting to 1.")
                else:
                    print("Defaulting to 1 impostor.")


            game_instance = Game(num_players=num_total_players, num_impostors=num_imps)
            game_instance.start_game()

        except ValueError:
            print("Invalid input. Please enter numbers.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            # break # Option to break loop on critical error

        print_separator()
        again = input("Play again? (yes/no): ").lower()
        if again != 'yes' and again != 'y':
            typewriter_print("\nThanks for playing! Goodbye!", 0.05)
            break
