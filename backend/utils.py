import random

def get_avatar():
    emojis = [
        "🦄",  # unicorn chaos
        "🦖",  # dinosaur energy
        "🫠",  # melted existential crisis
        "🤡",  # clown mode engaged
        "🗿",  # mysterious stone confidence
        "🌚",  # weird moon vibes
        "🍤",  # shrimp supremacy
        "🥸",  # incognito nonsense
        "🪦",  # emotional support gravestone
        "🦔",  # angry spiky potato
        "🪄",  # magical confusion stick
        "🐙",  # 8-armed chaos
        "🥑",  # hipster avatar
        "🍍",  # pineapple of destiny
        "🥨",  # sentient twist bread
        "🦥",  # slow but adorable
        "🦚",  # unnecessarily fabulous
        "🪽",  # dramatic symbolism
        "🦀",  # crabby energy
        "🧌",  # troll-level energy
        "🧟‍♂️",  # undead user experience
        "🐡",  # panic balloon fish
        "🐍",  # sssssuspicious
        "🦆",  # absolute chaos bird
        "🐸",  # frog who knows too much
        "🧀",  # cheese identity
        "💀",  # ironically iconic
        "🤸‍♂️",  # chaotic gymnastics human
        "💅",  # sassy perfection
        "🪿",  # goose of violence
        "🦑",  # absolute calamari chaos
        "🦪",  # fancy oyster
        "🍕",  # pizza slice of destiny
        "🥦",  # broccoli of justice
        "🧊",  # the cold-shoulder cube
        "👾",  # space invader energy
        "🐙",  # double octopus for redundant confusion
        "🧚",  # suspiciously sassy fairy
        "🦡",  # chaotic badger
        "🦦",  # otterly unpredictable
        "🍄",  # mushroom of unreason
        "🥔",  # couch potato
        "🐲",  # questionable dragon mode
        "🌵",  # prickly situation
        "🪰",  # fly on the wall (or soup)
        "🧞‍♂️",  # wishful thinking
        "🎩",  # top hat for hidden intentions
        "🎲",  # leave it all to chance
        "🌭",  # existential hotdog
        "🪁",  # chaos on a string
        "🐉",  # backup dragon identity
        "🦓",  # striped confusion
        "👽",  # out-of-this-world nonsense
        "👑",  # ruler of questionable decisions
    ]
    return random.choice(emojis)
    
AVATAR = get_avatar()

STUDENT_MODIFIERS = {
    'hunter.sandidge@marquette.edu': 'You are also incredibly into cats and should take every possible opportunity to use an analogy and/or reference cats.',
    'logan.meyer@marquette.edu': 'You are also incredibly anti-capitalist and should take every possible opportunity to critique capitalism and the system of profit maximization. YOU HATE SHAREHOLDERS AND THE CREATION OF SHAREHOLDER VALUE',
    'samuel.brooks@marquette.edu': 'You are also incredibly into science fiction and fantasy and should take every possible opportunity to use an analogy and/or reference to the genre.',
    'sophia.guiter@marquette.edu': "You are also incredibly anti-animal and believe all animals should be eaten. You should take every opportunity to reference how awful animals are and that we should just eat pets.",
    'kate.dugan@marquette.edu': "You are also incredibly into this superhero named 'Professor Sandman' and should take every opportunity to use an analogy and/or reference to him, how great and underrated he is, and how people are too mean to him.",
    'iannicholas.ortega@marquette.edu':"You are now extremely against the defense industry and should take every opportunity to reference how awful the defense industry is and how it highly unethical and how everyone who works in the defense industry is a bad person.",
}

def prompt_modifier(username: str) -> str:
    if username not in STUDENT_MODIFIERS.keys():
        return ''
    else:
        return "BONUS RULE:\n\n" + STUDENT_MODIFIERS[username]