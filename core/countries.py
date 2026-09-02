"""
countries.py — every country, its flag, its people and its capital.

One source, two consumers, and neither of them may be a hand-typed list of
wherever the toolkit last ran:

  fold/src/flags.js   generated from here, so a team from anywhere gets its flag
  feedback/terms.py   the ban list, so a summary cannot name a place

The flag emoji is not stored. It is computed from the two-letter code by
shifting each letter into the Unicode regional-indicator block, which is how
flag emoji are actually built — so there is nothing to keep up to date and no
country can be accidentally left out with a blank next to it.

Region strings come from your Tabbycat institution records, and tab writers
spell them however they like, so `flag()` also accepts the common alternates
("UK", "USA", "South Korea", "Vietnam", "Viet Nam").
"""

# Name | ISO 3166-1 alpha-2 | capital | demonyms (space separated)
_TABLE = """
Afghanistan|AF|Kabul|Afghan
Albania|AL|Tirana|Albanian
Algeria|DZ|Algiers|Algerian
Andorra|AD|Andorra la Vella|Andorran
Angola|AO|Luanda|Angolan
Argentina|AR|Buenos Aires|Argentine Argentinian
Armenia|AM|Yerevan|Armenian
Australia|AU|Canberra|Australian
Austria|AT|Vienna|Austrian
Azerbaijan|AZ|Baku|Azerbaijani
Bahamas|BS|Nassau|Bahamian
Bahrain|BH|Manama|Bahraini
Bangladesh|BD|Dhaka|Bangladeshi
Barbados|BB|Bridgetown|Barbadian
Belarus|BY|Minsk|Belarusian
Belgium|BE|Brussels|Belgian
Belize|BZ|Belmopan|Belizean
Benin|BJ|Porto-Novo|Beninese
Bhutan|BT|Thimphu|Bhutanese
Bolivia|BO|La Paz|Bolivian
Bosnia and Herzegovina|BA|Sarajevo|Bosnian Herzegovinian
Botswana|BW|Gaborone|Botswanan
Brazil|BR|Brasilia|Brazilian
Brunei|BN|Bandar Seri Begawan|Bruneian
Bulgaria|BG|Sofia|Bulgarian
Burkina Faso|BF|Ouagadougou|Burkinabe
Burundi|BI|Gitega|Burundian
Cambodia|KH|Phnom Penh|Cambodian Khmer
Cameroon|CM|Yaounde|Cameroonian
Canada|CA|Ottawa|Canadian
Cape Verde|CV|Praia|Cape Verdean
Central African Republic|CF|Bangui|
Chad|TD|N'Djamena|Chadian
Chile|CL|Santiago|Chilean
China|CN|Beijing|Chinese
Colombia|CO|Bogota|Colombian
Comoros|KM|Moroni|Comoran
Costa Rica|CR|San Jose|Costa Rican
Croatia|HR|Zagreb|Croatian
Cuba|CU|Havana|Cuban
Cyprus|CY|Nicosia|Cypriot
Czechia|CZ|Prague|Czech
Democratic Republic of the Congo|CD|Kinshasa|Congolese
Denmark|DK|Copenhagen|Danish Dane
Djibouti|DJ|Djibouti|Djiboutian
Dominica|DM|Roseau|Dominican
Dominican Republic|DO|Santo Domingo|
Ecuador|EC|Quito|Ecuadorian
Egypt|EG|Cairo|Egyptian
El Salvador|SV|San Salvador|Salvadoran
Equatorial Guinea|GQ|Malabo|
Eritrea|ER|Asmara|Eritrean
Estonia|EE|Tallinn|Estonian
Eswatini|SZ|Mbabane|Swazi
Ethiopia|ET|Addis Ababa|Ethiopian
Fiji|FJ|Suva|Fijian
Finland|FI|Helsinki|Finnish Finn
France|FR|Paris|French
Gabon|GA|Libreville|Gabonese
Gambia|GM|Banjul|Gambian
Georgia|GE|Tbilisi|Georgian
Germany|DE|Berlin|German
Ghana|GH|Accra|Ghanaian
Greece|GR|Athens|Greek
Grenada|GD|St George's|Grenadian
Guatemala|GT|Guatemala City|Guatemalan
Guinea|GN|Conakry|Guinean
Guyana|GY|Georgetown|Guyanese
Haiti|HT|Port-au-Prince|Haitian
Honduras|HN|Tegucigalpa|Honduran
Hong Kong|HK|Hong Kong|Hongkonger
Hungary|HU|Budapest|Hungarian
Iceland|IS|Reykjavik|Icelandic Icelander
India|IN|New Delhi|Indian
Indonesia|ID|Jakarta|Indonesian
Iran|IR|Tehran|Iranian
Iraq|IQ|Baghdad|Iraqi
Ireland|IE|Dublin|Irish
Israel|IL|Jerusalem|Israeli
Italy|IT|Rome|Italian
Ivory Coast|CI|Yamoussoukro|Ivorian
Jamaica|JM|Kingston|Jamaican
Japan|JP|Tokyo|Japanese
Jordan|JO|Amman|Jordanian
Kazakhstan|KZ|Astana|Kazakh
Kenya|KE|Nairobi|Kenyan
Kiribati|KI|Tarawa|I-Kiribati
Kosovo|XK|Pristina|Kosovan
Kuwait|KW|Kuwait City|Kuwaiti
Kyrgyzstan|KG|Bishkek|Kyrgyz
Laos|LA|Vientiane|Laotian Lao
Latvia|LV|Riga|Latvian
Lebanon|LB|Beirut|Lebanese
Lesotho|LS|Maseru|Basotho
Liberia|LR|Monrovia|Liberian
Libya|LY|Tripoli|Libyan
Liechtenstein|LI|Vaduz|
Lithuania|LT|Vilnius|Lithuanian
Luxembourg|LU|Luxembourg|Luxembourgish
Macau|MO|Macau|Macanese
Madagascar|MG|Antananarivo|Malagasy
Malawi|MW|Lilongwe|Malawian
Malaysia|MY|Kuala Lumpur|Malaysian
Maldives|MV|Male|Maldivian
Mali|ML|Bamako|Malian
Malta|MT|Valletta|Maltese
Marshall Islands|MH|Majuro|
Mauritania|MR|Nouakchott|Mauritanian
Mauritius|MU|Port Louis|Mauritian
Mexico|MX|Mexico City|Mexican
Micronesia|FM|Palikir|
Moldova|MD|Chisinau|Moldovan
Monaco|MC|Monaco|Monegasque
Mongolia|MN|Ulaanbaatar|Mongolian
Montenegro|ME|Podgorica|Montenegrin
Morocco|MA|Rabat|Moroccan
Mozambique|MZ|Maputo|Mozambican
Myanmar|MM|Naypyidaw|Burmese
Namibia|NA|Windhoek|Namibian
Nauru|NR|Yaren|Nauruan
Nepal|NP|Kathmandu|Nepali Nepalese
Netherlands|NL|Amsterdam|Dutch
New Zealand|NZ|Wellington|Kiwi
Nicaragua|NI|Managua|Nicaraguan
Niger|NE|Niamey|Nigerien
Nigeria|NG|Abuja|Nigerian
North Macedonia|MK|Skopje|Macedonian
Norway|NO|Oslo|Norwegian
Oman|OM|Muscat|Omani
Pakistan|PK|Islamabad|Pakistani
Palau|PW|Ngerulmud|Palauan
Palestine|PS|Ramallah|Palestinian
Panama|PA|Panama City|Panamanian
Papua New Guinea|PG|Port Moresby|
Paraguay|PY|Asuncion|Paraguayan
Peru|PE|Lima|Peruvian
Philippines|PH|Manila|Filipino Filipina Philippine
Poland|PL|Warsaw|Polish Pole
Portugal|PT|Lisbon|Portuguese
Qatar|QA|Doha|Qatari
Romania|RO|Bucharest|Romanian
Russia|RU|Moscow|Russian
Rwanda|RW|Kigali|Rwandan
Samoa|WS|Apia|Samoan
Saudi Arabia|SA|Riyadh|Saudi
Senegal|SN|Dakar|Senegalese
Serbia|RS|Belgrade|Serbian Serb
Seychelles|SC|Victoria|Seychellois
Sierra Leone|SL|Freetown|
Singapore|SG|Singapore|Singaporean
Slovakia|SK|Bratislava|Slovak
Slovenia|SI|Ljubljana|Slovenian Slovene
Solomon Islands|SB|Honiara|
Somalia|SO|Mogadishu|Somali
South Africa|ZA|Pretoria|South African
South Korea|KR|Seoul|Korean
South Sudan|SS|Juba|
Spain|ES|Madrid|Spanish Spaniard
Sri Lanka|LK|Colombo|Sri Lankan Sinhalese
Sudan|SD|Khartoum|Sudanese
Suriname|SR|Paramaribo|Surinamese
Sweden|SE|Stockholm|Swedish Swede
Switzerland|CH|Bern|Swiss
Syria|SY|Damascus|Syrian
Taiwan|TW|Taipei|Taiwanese
Tajikistan|TJ|Dushanbe|Tajik
Tanzania|TZ|Dodoma|Tanzanian
Thailand|TH|Bangkok|Thai
Timor-Leste|TL|Dili|Timorese
Togo|TG|Lome|Togolese
Tonga|TO|Nuku'alofa|Tongan
Trinidad and Tobago|TT|Port of Spain|Trinidadian
Tunisia|TN|Tunis|Tunisian
Turkey|TR|Ankara|Turkish Turk
Turkmenistan|TM|Ashgabat|Turkmen
Tuvalu|TV|Funafuti|Tuvaluan
Uganda|UG|Kampala|Ugandan
Ukraine|UA|Kyiv|Ukrainian
United Arab Emirates|AE|Abu Dhabi|Emirati
United Kingdom|GB|London|British Briton
United States|US|Washington|American
Uruguay|UY|Montevideo|Uruguayan
Uzbekistan|UZ|Tashkent|Uzbek
Vanuatu|VU|Port Vila|Vanuatuan
Venezuela|VE|Caracas|Venezuelan
Vietnam|VN|Hanoi|Vietnamese
Yemen|YE|Sanaa|Yemeni
Zambia|ZM|Lusaka|Zambian
Zimbabwe|ZW|Harare|Zimbabwean
"""

# How tab writers actually spell things, mapped to the canonical name above.
ALIASES = {
    "UK": "United Kingdom", "Great Britain": "United Kingdom", "Britain": "United Kingdom",
    "England": "United Kingdom", "Scotland": "United Kingdom", "Wales": "United Kingdom",
    "Northern Ireland": "United Kingdom",
    "USA": "United States", "U.S.": "United States", "US": "United States",
    "United States of America": "United States", "America": "United States",
    "Korea": "South Korea", "Republic of Korea": "South Korea", "ROK": "South Korea",
    "Viet Nam": "Vietnam", "UAE": "United Arab Emirates", "Emirates": "United Arab Emirates",
    "Czech Republic": "Czechia", "Holland": "Netherlands", "Burma": "Myanmar",
    "Macao": "Macau", "Hongkong": "Hong Kong", "PRC": "China",
    "Cote d'Ivoire": "Ivory Coast", "Swaziland": "Eswatini", "Turkiye": "Turkey",
    "East Timor": "Timor-Leste", "Cabo Verde": "Cape Verde", "DRC": "Democratic Republic of the Congo",
    "Congo": "Democratic Republic of the Congo",
}

# Big cities that are not their country's capital. A summary naming one of these
# places the tournament just as surely as naming the country.
EXTRA_CITIES = """Mumbai Bengaluru Bangalore Chennai Kolkata Hyderabad Pune Ahmedabad
Karachi Lahore Chittagong Ho Chi Minh Saigon Da Nang Surabaya Bandung Medan
Cebu Davao Penang Johor Ipoh Shanghai Guangzhou Shenzhen Chengdu Wuhan Osaka
Kyoto Yokohama Busan Incheon Kaohsiung Almaty Istanbul Casablanca Lagos Ibadan
Kano Nairobi Mombasa Cape Town Johannesburg Durban Alexandria Sydney Melbourne
Brisbane Perth Auckland Toronto Montreal Vancouver New York Los Angeles Chicago
Boston Houston Seattle Sao Paulo Rio de Janeiro Buenos Aires Bogota Lima
Guadalajara Monterrey Barcelona Milan Munich Frankfurt Hamburg Manchester
Birmingham Glasgow Edinburgh Dublin Rotterdam Antwerp Zurich Geneva Krakow
St Petersburg Novosibirsk Tel Aviv Dubai Sharjah Jeddah Mecca Basra Isfahan
Lucknow Jaipur Kanpur Nagpur Indore Coimbatore Kochi Guwahati""".split("\n")


def _rows():
    for line in _TABLE.strip().splitlines():
        name, a2, cap, dem = (line.split("|") + ["", "", "", ""])[:4]
        yield name.strip(), a2.strip(), cap.strip(), dem.split()


COUNTRIES = {name: a2 for name, a2, _, _ in _rows()}
CAPITALS = {name: cap for name, _, cap, _ in _rows() if cap}
DEMONYMS = {name: dem for name, _, _, dem in _rows()}


def alpha2(region):
    """Two-letter code for however the tab spelled a region. None if unknown."""
    if not region:
        return None
    r = str(region).strip()
    r = ALIASES.get(r, ALIASES.get(r.title(), r))
    if r in COUNTRIES:
        return COUNTRIES[r]
    low = {k.lower(): v for k, v in COUNTRIES.items()}
    return low.get(r.lower())


def flag(region):
    """The flag emoji for a region, built from its code. None if unknown."""
    a2 = alpha2(region)
    if not a2 or len(a2) != 2:
        return None
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in a2.upper())


def place_words():
    """Every word that names a place, for the feedback ban list. Multi-word names
    are returned whole as well as in their parts, so both "Sri Lanka" and
    "Lankan" are caught."""
    out = set()
    for name, a2, cap, dem in _rows():
        out.add(name)
        out.update(dem)
        if cap:
            out.add(cap)
    out.update(ALIASES)
    for city in EXTRA_CITIES:
        out.add(city.strip())
    # Single tokens of multi-word names, but only distinctive ones — "New",
    # "South" and "Republic" would otherwise be banned from every summary.
    GENERIC_PARTS = {"new", "south", "north", "east", "west", "republic", "united",
                     "states", "kingdom", "and", "of", "the", "city", "central",
                     "guinea", "islands", "saint", "st", "port", "san", "arabia"}
    for name in list(out):
        for tok in str(name).split():
            if len(tok) > 3 and tok.lower() not in GENERIC_PARTS:
                out.add(tok)
    return {w for w in out if len(w) > 3}


if __name__ == "__main__":
    print(f"{len(COUNTRIES)} countries, {len(place_words())} place words")
    for r in ("Vietnam", "Viet Nam", "UK", "Korea", "USA", "Hong Kong", "Nowhere"):
        print(f"  {r:12s} -> {alpha2(r)}  {flag(r) or '(no flag)'}")
