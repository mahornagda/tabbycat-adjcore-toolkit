"""
common_english.py — the ordinary words of English, so the feedback gate can tell
a distinctive word from a plain one.

WHY THIS FILE EXISTS
--------------------
A summary must not repeat a word that only the motion could have supplied,
because a distinctive word names the round. Working out which words those are
means subtracting the ordinary ones, and the only tool to hand was
/usr/share/dict/words — which contains 235,000 entries including every rare and
archaic word in the language, so almost nothing counts as ordinary and almost
every word gets banned.

The first version of the gate solved that by hand: a list of the words that
happened to appear in one tournament's motions. It worked there and nowhere
else, which is the whole problem this toolkit is trying not to have.

So: a frequency list instead. Roughly the most common words in written English,
which is a property of the language and not of a tournament. A motion word
outside this list is the kind of word worth banning ("tenure", "picketing",
"litigation"); a motion word inside it is not ("work", "land", "large",
"individual"), and banning those makes it impossible to write about judging at
all.

If your motions keep tripping the gate on a word that is plainly ordinary, add
it here. That is the intended way to tune this, and it stays true for the next
tournament rather than only for yours.
"""

WORDS = set("""
a able about above accept according account across act action activity actually
add address administration admit adult affect after again against age agency
agent ago agree agreement ahead air all allow almost alone along already also
although always american among amount analysis and animal another answer any
anyone anything appear apply approach area argue arm around arrive art article
artist as ask assume at attack attention attorney audience author authority
available avoid away baby back bad bag ball bank bar base be beat beautiful
because become bed before begin behavior behind believe benefit best better
between beyond big bill billion bit black blood blue board body book born both
box boy break bring brother budget build building business but buy by call
camera campaign can cancer candidate capital car card care career carry case
catch cause cell center central century certain certainly chair challenge chance
change character charge check child choice choose church citizen city civil
claim class clear clearly close coach cold collection college color come
commercial common community company compare computer concern condition
conference congress consider consumer contain continue control cost could
country couple course court cover create crime cultural culture cup current
customer cut dark data daughter day dead deal death debate decade decide
decision deep defense degree democrat democratic describe design despite detail
determine develop development die difference different difficult dinner
direction director discuss discussion disease do doctor dog door down draw dream
drive drop drug during each early east easy eat economic economy edge education
effect effort eight either election else employee end energy enjoy enough enter
entire environment environmental especially establish even evening event ever
every everybody everyone everything evidence exactly example executive exist
expect experience expert explain eye face fact factor fail fall family far fast
father fear federal feel feeling few field fight figure fill film final finally
financial find fine finger finish fire firm first fish five floor fly focus
follow food foot for force foreign forget form former forward four free
friend from front full fund future game garden gas general generation get girl
give glass go goal good government great green ground group grow growth guess
gun guy hair half hand hang happen happy hard have he head health hear heart
heat heavy help her here herself high him himself his history hit hold home hope
hospital hot hotel hour house how however huge human hundred husband i idea
identify if image imagine impact important improve in include including increase
indeed indicate individual industry information inside instead institution
interest interesting international interview into investment involve issue it
item its itself job join just keep key kid kill kind kitchen know knowledge land
language large last late later laugh law lawyer lay lead leader learn least
leave left leg legal less let letter level lie life light like likely line list
listen little live local long look lose loss lot love low machine magazine main
maintain major majority make man manage management manager many market marriage
material matter may maybe me mean measure media medical meet meeting member
memory mention message method middle might military million mind minute miss
mission model modern moment money month more morning most mother mouth move
movement movie much music must my myself name nation national natural nature
near nearly necessary need network never new news newspaper next nice night no
none nor north not note nothing notice now number occur of off offer office
officer official often oh oil ok old on once one only onto open operation
opportunity option or order organization other others our out outside over own
owner page pain painting paper parent part participant particular particularly
partner party pass past patient pattern pay peace people per perform performance
perhaps period person personal phone physical pick picture piece place plan
plant play player point police policy political politics poor popular population
position positive possible power practice prepare present president pressure
pretty prevent price private probably problem process produce product production
professional professor program project property protect prove provide public
pull purpose push put quality question quickly quite race radio raise range rate
rather reach read ready real reality realize really reason receive recent
recently recognize record red reduce reflect region relate relationship
religious remain remember remove report represent republican require research
resource respond response responsibility rest result return reveal rich right
rise risk road rock role room rule run safe same save say scene school science
scientist score sea season seat second section security see seek seem sell send
senior sense series serious serve service set seven several sex sexual shake
share she shoot short shot should shoulder show side sign significant similar
simple simply since sing single sister sit site situation six size skill skin
small smile so social society soldier some somebody someone something sometimes
son song soon sort sound source south southern space speak special specific
speech spend sport spring staff stage stand standard star start state statement
station stay step still stock stop store story strategy street strong structure
student study stuff style subject success successful such suddenly suffer
suggest summer support sure surface system table take talk task tax teach
teacher team technology television tell ten tend term test than thank that the
their them themselves then theory there these they thing think third this those
though thought thousand threat three through throughout throw thus time to today
together tonight too top total tough toward town trade traditional training
travel treat treatment tree trial trip trouble true truth try turn tv two type
under understand unit until up upon us use usually value various very victim
view violence visit voice vote wait walk wall want war watch water way we weapon
wear week weight well west western what whatever when where whether which while
white who whole whom whose why wide wife will win wind window wish with within
without woman wonder word work worker world worry would write writer wrong yard
yeah year yes yet you young your yourself
argument argue claim reason evidence example point points case make made making
weight weigh clear clearly explain explanation follow followed structure
structured signpost signposting compare comparison comparative track tracking
respond response engage engagement analysis analyse deliver delivery pace clarity
tone confident confidence decision decide call ruling rule burden burdens
mechanism impact impacts principle practical framing frame credit credited
generous fair fairness consistent consistency accurate accuracy honest honestly
thorough careful carefully sharp firm calm warm kind kindly patient rushed slow
quick brief short long detailed general specific useful useless helpful
replace replaced replacing refuse refused refusing publish published primary
cross band remove removed removing require required allow allowed prevent
prevented reduce reduced raise raised lower lowered grant granted permit
permitted accept accepted reject rejected admit admitted apply applied assume
assumed avoid avoided cover covered describe described address addressed handle
handled manage managed notice noticed mention mentioned prefer preferred
abandon abandoned adopt adopted pursue pursued implement implemented consider
considered maintain maintained academic amateur retail salary software
scheduling municipal heritage
""".split())


def is_ordinary(word):
    """True if this is a plain English word rather than a distinctive one."""
    w = str(word or "").lower().strip("'-")
    if w in WORDS:
        return True
    # cheap morphology, so "requiring" is as ordinary as "require"
    for suffix in ("s", "es", "ed", "ing", "ly", "er", "est", "ies", "ment"):
        if w.endswith(suffix):
            stem = w[: -len(suffix)]
            if stem in WORDS or (stem + "e") in WORDS or (stem + "y") in WORDS:
                return True
    return False


if __name__ == "__main__":
    print(f"{len(WORDS)} common words")
    for w in ("work", "individual", "land", "large", "requiring", "tenure",
              "picketing", "litigation", "birthright", "comparative"):
        print(f"  {w:12s} {'ordinary' if is_ordinary(w) else 'DISTINCTIVE — banned'}")
