import random

from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from .models import pokemon as PokemonModel
from .pokeapi import fetch_and_create_pokemon

MAX_TEAM_SIZE = 5
FIRST_GEN_LIMIT = 251


def _get_team(session, key):
    raw = session.get(key, [])
    if not isinstance(raw, list):
        return []
    cleaned = []
    for val in raw:
        try:
            cleaned.append(int(val))
        except (TypeError, ValueError):
            continue
    return cleaned


def _save_team(session, key, values):
    session[key] = values
    session.modified = True


def _ensure_pokemon_exists(pokemon_id, errors):
    if pokemon_id < 1 or pokemon_id > FIRST_GEN_LIMIT:
        errors.append(f"Le pokemon #{pokemon_id} n'est pas disponible (1-{FIRST_GEN_LIMIT}).")
        return None
    try:
        return PokemonModel.objects.get(pk=pokemon_id)
    except PokemonModel.DoesNotExist:
        fetched = fetch_and_create_pokemon(pokemon_id, PokemonModel)
        if not fetched:
            errors.append(f"Impossible de récupérer le pokemon #{pokemon_id} depuis PokeAPI.")
            return None
        return fetched


def _load_team_objects(team_ids, errors):
    objects_by_id = {p.pk: p for p in PokemonModel.objects.filter(pk__in=team_ids)}
    ordered = []
    for pid in team_ids:
        poke = objects_by_id.get(pid)
        if not poke:
            poke = _ensure_pokemon_exists(pid, errors)
            if poke:
                objects_by_id[pid] = poke
        if poke:
            ordered.append(poke)
    return ordered


def _ai_team(errors):
    # generate a random AI team within first 251 ids
    sample_ids = random.sample(range(1, FIRST_GEN_LIMIT + 1), k=MAX_TEAM_SIZE)
    valid_ids = []
    for pid in sample_ids:
        poke = _ensure_pokemon_exists(pid, errors)
        if poke:
            valid_ids.append(pid)
    return valid_ids


def _combat_score(p):
    return (
        p.attack * 1.2
        + p.special_attack * 1.1
        + p.speed * 1.0
        + p.defense * 0.9
        + p.special_defense * 0.9
        + p.hp * 0.6
    )


def _simulate_battle(team_a, team_b):
    rounds = []
    score_a = 0
    score_b = 0
    total = max(len(team_a), len(team_b))
    for idx in range(total):
        poke_a = team_a[idx] if idx < len(team_a) else None
        poke_b = team_b[idx] if idx < len(team_b) else None
        if poke_a and not poke_b:
            rounds.append({'index': idx + 1, 'winner': 'A', 'reason': 'Team B incomplet', 'a': poke_a, 'b': None})
            score_a += 1
            continue
        if poke_b and not poke_a:
            rounds.append({'index': idx + 1, 'winner': 'B', 'reason': 'Team A incomplet', 'a': None, 'b': poke_b})
            score_b += 1
            continue
        power_a = _combat_score(poke_a) + random.uniform(-10, 10)
        power_b = _combat_score(poke_b) + random.uniform(-10, 10)
        if power_a > power_b:
            score_a += 1
            winner = 'A'
        elif power_b > power_a:
            score_b += 1
            winner = 'B'
        else:
            winner = 'Draw'
        rounds.append({
            'index': idx + 1,
            'winner': winner,
            'reason': f"{power_a:.1f} vs {power_b:.1f}",
            'a': poke_a,
            'b': poke_b,
        })
    if score_a > score_b:
        winner_text = 'Victoire de l\'equipe A'
    elif score_b > score_a:
        winner_text = 'Victoire de l\'equipe B'
    else:
        winner_text = 'Match nul'
    return {
        'rounds': rounds,
        'score_a': score_a,
        'score_b': score_b,
        'winner_text': winner_text,
    }

def index(request):
    text = 'Welcome to the Pokedex Application!'
    q = request.GET.get('q', '').strip()
    pokemons_qs = PokemonModel.objects.filter(number__lte=FIRST_GEN_LIMIT).order_by('number')
    if q:
        # rechercher par numéro exact ou par nom partiel
        if q.isdigit():
            pokemons_qs = pokemons_qs.filter(Q(number=int(q)) | Q(name__icontains=q))
        else:
            pokemons_qs = pokemons_qs.filter(name__icontains=q)
    # pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(pokemons_qs, 24)
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    return render(request, 'pokedexApp/index.html', {'text': text, 'page_obj': page_obj, 'q': q})


def pokemon(request, pokemon_id):
    # Essayer de récupérer depuis la base
    try:
        poke = PokemonModel.objects.get(pk=pokemon_id)
    except PokemonModel.DoesNotExist:
        # Tentative de récupération via PokeAPI
        poke = fetch_and_create_pokemon(pokemon_id, PokemonModel)
        if not poke:
            # Toujours introuvable
            from django.http import Http404
            raise Http404('No pokemon matches the given query.')
    context = {'pokemon': poke}
    return render(request, 'pokedexApp/pokemon.html', context)

# Vue pour afficher la page de formation
def formation(request):
    errors = []
    infos = []
    battle_result = None

    team_a_ids = _get_team(request.session, 'team_a')
    team_b_ids = _get_team(request.session, 'team_b')

    action = None
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            target = request.POST.get('team', 'A')
            team_key = 'team_a' if target == 'A' else 'team_b'
            try:
                pid = int(request.POST.get('pokemon_id', ''))
            except (TypeError, ValueError):
                errors.append('Identifiant de pokemon invalide.')
                pid = None
            if pid:
                current_ids = team_a_ids if team_key == 'team_a' else team_b_ids
                if pid in current_ids:
                    errors.append('Ce pokemon est deja dans cette equipe.')
                elif len(current_ids) >= MAX_TEAM_SIZE:
                    errors.append('Equipe pleine (5 pokemons max).')
                else:
                    poke = _ensure_pokemon_exists(pid, errors)
                    if poke:
                        current_ids.append(poke.pk)
                        infos.append(f'{poke.name} ajoute a l\'equipe {target}.')
                if team_key == 'team_a':
                    team_a_ids = current_ids
                else:
                    team_b_ids = current_ids

        elif action == 'remove':
            target = request.POST.get('team', 'A')
            try:
                pid = int(request.POST.get('pokemon_id', ''))
            except (TypeError, ValueError):
                pid = None
            if target == 'A':
                if pid in team_a_ids:
                    team_a_ids = [i for i in team_a_ids if i != pid]
            else:
                if pid in team_b_ids:
                    team_b_ids = [i for i in team_b_ids if i != pid]

        elif action == 'clear':
            target = request.POST.get('team', 'both')
            if target in ('A', 'both'):
                team_a_ids = []
            if target in ('B', 'both'):
                team_b_ids = []

        elif action == 'ai_fill':
            team_b_ids = _ai_team(errors)
            if not errors:
                infos.append('Equipe B generee automatiquement.')

        elif action == 'battle':
            # handled after teams are loaded
            pass

        _save_team(request.session, 'team_a', team_a_ids)
        _save_team(request.session, 'team_b', team_b_ids)

    team_a = _load_team_objects(team_a_ids, errors)
    team_b = _load_team_objects(team_b_ids, errors)

    if action == 'battle' and not errors:
        if not team_a or not team_b:
            errors.append('Les deux equipes doivent contenir au moins un pokemon.')
        else:
            battle_result = _simulate_battle(team_a, team_b)

    # listing des pokemons pour l'ajout
    q = request.GET.get('q', '').strip()
    pokemons_qs = PokemonModel.objects.filter(number__lte=FIRST_GEN_LIMIT).order_by('number')
    if q:
        if q.isdigit():
            pokemons_qs = pokemons_qs.filter(Q(number=int(q)) | Q(name__icontains=q))
        else:
            pokemons_qs = pokemons_qs.filter(name__icontains=q)
    page = request.GET.get('page', 1)
    paginator = Paginator(pokemons_qs, 20)
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {
        'team_a': team_a,
        'team_b': team_b,
        'team_a_ids': team_a_ids,
        'team_b_ids': team_b_ids,
        'page_obj': page_obj,
        'q': q,
        'errors': errors,
        'infos': infos,
        'battle': battle_result,
    }
    return render(request, 'pokedexApp/formation.html', context)
