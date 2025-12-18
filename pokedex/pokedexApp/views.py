from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from .models import pokemon as PokemonModel
from .pokeapi import fetch_and_create_pokemon

def index(request):
    text = 'Welcome to the Pokedex Application!'
    q = request.GET.get('q', '').strip()
    pokemons_qs = PokemonModel.objects.all().order_by('number')
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
    return render(request, 'pokedexApp/formation.html', {})
