from _asynchronise_2 import Asynchronise
import random
asyncer = Asynchronise()
import asyncio
import typing
class Newspaper:
    def __init__(self, headline: str) -> None:
        self.headline = headline
        self.authors = []
    def __repr__(self) -> str:
        return f"Newspaper({self.headline})"

@asyncer.send
async def generate_newspaper():
    subject = ["Russia", "China", "The President", "H. P. Lovecraft", "The Moon"]
    verb = ["eats", "destroys", "kills", "saves"]
    obj = ["a banana", "a cat", "a dog", "a human", "a robot"]
    while True:
        yield Newspaper(f"{random.choice(subject)} {random.choice(verb)} {random.choice(obj)}"), "newspaper_no_authors"

def generate_authors():
    import time
    time.sleep(0.3)
    first_name_consonants = ["K", "P", "S", "T", "R", "L", "N", "M", "H", "W", "Y", "B", "G", "D", "J", "Z", "C", "Q", "X", "V", "F", "A", "E", "I", "O", "U"]
    first_name_syllable = ["agga", "iggy", "ogda", "edda"]
    last_name = str(random.randint(1, 9999))
    return f"{random.choice(first_name_consonants)}{random.choice(first_name_syllable)} {last_name}"

@asyncer.send
@asyncer.collect()
def add_author(newspaper_no_authors: Newspaper):
    author = generate_authors()
    yield author, "author"
    newspaper_no_authors.authors.append(author)
    yield newspaper_no_authors, "newspaper_with_authors"

@asyncer.collect()
def print_newspaper(newspaper_with_authors: Newspaper):
    print(newspaper_with_authors)

@asyncer.collect()
def print_author(author: str):
    print(author)

async def run():
    i = 0
    async for newspaper in generate_newspaper():
        i += 1
        if i > 5:
            break
        pass
    await asyncio.sleep(2)

asyncio.run(run())