import json
try:
    import requests
except Exception:
    requests = None

from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

POKE_API_BASE = 'https://pokeapi.co/api/v2'


def _get_json(url, timeout=10):
    # prefer requests if available
    if requests:
        try:
            r = requests.get(url, headers={'User-Agent': 'pokedex-app/1.0'}, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            return None
        except Exception:
            return None
    # fallback
    req = Request(url, headers={'User-Agent': 'pokedex-app/1.0'})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except HTTPError:
        return None
    except URLError:
        return None


def fetch_pokemon_data(pokemon_id):
    """Récupère les données publiques d'un Pokémon depuis PokeAPI.
    Retourne un dict avec keys: number, name, typePokemon, image, description
    Ou None en cas d'erreur.
    """
    purl = f"{POKE_API_BASE}/pokemon/{pokemon_id}/"
    pdata = _get_json(purl)
    if not pdata:
        return None

    surl = f"{POKE_API_BASE}/pokemon-species/{pokemon_id}/"
    sdata = _get_json(surl)

    # name
    name = pdata.get('name')
    # types
    types = [t['type']['name'] for t in pdata.get('types', [])]
    type_str = '/'.join(types)
    # image: use sprites.front_default
    image = pdata.get('sprites', {}).get('front_default') or ''
    # description: try to get english flavor text
    description = ''
    if sdata:
        for entry in sdata.get('flavor_text_entries', []):
            lang = entry.get('language', {}).get('name')
            if lang == 'en':
                # normalize whitespace and remove newlines
                description = entry.get('flavor_text', '').replace('\n', ' ').replace('\f', ' ')
                break

    # base stats
    stats_map = {}
    for stat in pdata.get('stats', []):
        key = stat.get('stat', {}).get('name')
        if key:
            stats_map[key] = stat.get('base_stat', 0)

    return {
        'number': int(pokemon_id),
        'name': name.title() if name else '',
        'typePokemon': type_str.title(),
        'image': image or '',
        'description': description,
        'hp': stats_map.get('hp', 0),
        'attack': stats_map.get('attack', 0),
        'defense': stats_map.get('defense', 0),
        'special_attack': stats_map.get('special-attack', 0),
        'special_defense': stats_map.get('special-defense', 0),
        'speed': stats_map.get('speed', 0),
    }


def fetch_and_create_pokemon(pokemon_id, model_class):
    """Récupère depuis PokeAPI et crée/mettre à jour une instance du modèle donné.
    Retourne l'instance si OK, ou None en cas d'erreur.
    model_class doit être la classe Django du modèle (ex: pokedexApp.models.Pokemon)
    """
    data = fetch_pokemon_data(pokemon_id)
    if not data:
        return None

    # create or update
    obj, created = model_class.objects.update_or_create(
        pk=data['number'],
        defaults={
            'number': data['number'],
            'name': data['name'],
            'typePokemon': data['typePokemon'],
            'image': data['image'],
            'description': data['description'][:200],
            'hp': data['hp'],
            'attack': data['attack'],
            'defense': data['defense'],
            'special_attack': data['special_attack'],
            'special_defense': data['special_defense'],
            'speed': data['speed'],
        }
    )
    return obj
