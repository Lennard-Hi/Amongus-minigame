import random
import time

def play_find_the_impostor():
    players = ["Red", "Blue", "Green", "Yellow", "Pink", "Orange", "Black", "White", "Purple", "Cyan"]

    location_tasks = {
        "Electrical": ["fixing wires"],
        "Cafeteria": ["emptying trash"],
        "Engine Room": ["fueling engines"],
        "Admin": ["swiping card"],
        "Shields": ["priming shields"],
        "Storage": ["organizing boxes"],
        "Medbay": ["submitting scan"],
        "Weapons": ["clearing asteroids"],
        "Navigation": ["charting course"],
        "Reactor": ["starting reactor"],
        "Security": ["monitoring cameras"],
        "Communications": ["resetting comms"],
        "O2": ["cleaning O2 filter"]
    }

    rooms = list(location_tasks.keys())

    print("=============================")
    print("  Welcome to Find the Impostor!")
    print("=============================")
    print("\nA crewmate has been found DEAD! Listen to the alibis and deduce the impostor...\n")
    time.sleep(2)

    impostor = random.choice(players)
    alive_players = [p for p in players if p != impostor]
    victim = random.choice(alive_players)
    possible_reporters = [p for p in players if p not in [victim, impostor]]
    reporter = random.choice(possible_reporters)

    murder_room = random.choice(rooms)
    impostor_task = random.choice(location_tasks[murder_room])
    player_info = {
        impostor: {"location": murder_room, "task": impostor_task}
    }

    available_rooms = [r for r in rooms if r != murder_room]
    random.shuffle(available_rooms)

    # Assign roles
    roles = {}
    medic = random.choice([p for p in players if p not in [victim, impostor]])
    roles[medic] = "Medic"

    for player in players:
        if player in [victim, impostor]:
            continue
        room = available_rooms.pop() if available_rooms else random.choice(rooms)
        task = random.choice(location_tasks[room])
        player_info[player] = {"location": room, "task": task}

    victim_location = murder_room if random.random() < 0.7 else random.choice([r for r in rooms if r != murder_room])
    victim_task = random.choice(location_tasks[victim_location])
    player_info[victim] = {"location": victim_location, "task": victim_task}

    # Generate distributed sightings
    sightings = []
    for player in players:
        if player in [victim, impostor]:
            continue
        seen = None
        roll = random.random()
        if roll < 0.4:
            seen = impostor
        elif roll < 0.7:
            others = [p for p in players if p not in [player, victim, impostor]]
            if others:
                seen = random.choice(others)
        elif roll < 0.9:
            seen = victim
        if seen:
            location = player_info[seen]['location']
            sightings.append((player, seen, location))

    # Alibis
    print("\n--- Crewmate Statements ---")
    for player in sorted(players):
        if player == victim:
            continue
        info = player_info[player]
        role = f" ({roles[player]})" if player in roles else ""
        print(f"- {player}{role}: \"I was {info['task']} in {info['location']}.\"")
        time.sleep(0.4)

    # Medic scan
    print("\n--- SPECIAL ROLE INFO ---")
    print(f"- {medic} (Medic) confirms: \"I scanned {random.choice([p for p in players if p not in [medic, victim, impostor]])}. They're clear.\"")
    time.sleep(0.5)

    # Fact log
    print("\n--- FACT LOG ---")
    print(f"- {reporter} reported the dead body of {victim} in {murder_room}.")
    print(f"- Estimated time of death: ~30 seconds ago (body is cooling).")
    print(f"- {victim}'s last known location was {victim_location}.")
    for witness, seen, location in sightings:
        print(f"- {witness} saw {seen} in {location} recently.")
        time.sleep(0.4)

    print("=============================")

    # Suspicions
    suspects = [p for p in players if p not in [victim, reporter]]
    suspicions = {}
    for p in suspects:
        if random.random() < 0.3:
            target = random.choice([s for s in suspects if s != p])
            suspicions[p] = target

    if suspicions:
        print("\n--- SUSPECT STATEMENTS ---")
        for p, target in suspicions.items():
            print(f"- {p}: \"I think {target} is acting suspicious.\"")
            time.sleep(0.4)

    # Player's Guess
    guess = None
    while not guess:
        guess_input = input("\nWho do YOU vote as the impostor? (Enter color name): ").strip().title()
        if guess_input in players and guess_input != victim:
            guess = guess_input
        else:
            print(f"'{guess_input}' is invalid. Choose from: {', '.join([p for p in players if p != victim])}")

    # Reveal
    print("\nAnalyzing clues...")
    time.sleep(2)
    print("\n=============================")

    if guess == impostor:
        print(f"\n *** CORRECT! ***")
        print(f"{impostor} was the impostor!")
        print(f"They killed {victim} in {murder_room} and faked doing '{impostor_task}'.")
        print("You deduced the truth! Victory!")
    else:
        print(f"\n--- INCORRECT ---")
        print(f"You voted for {guess}, but the impostor was actually {impostor}!")
        print(f"{impostor} killed {victim} in {murder_room} and lied about their task.")
        print("The impostor escapes... Game Over.")

    print("=============================")

# --- Game Loop ---
if __name__ == "__main__":
    while True:
        play_find_the_impostor()
        again = input("\nPlay again? (yes/no): ").lower()
        if again != 'yes':
            print("\nThanks for playing! Goodbye!")
            break
