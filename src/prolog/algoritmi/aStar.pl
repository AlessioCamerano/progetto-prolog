% -------------------------------------------------------------------------
% Motore di ricerca A* 
% -------------------------------------------------------------------------

:- set_prolog_flag(stack_limit, 8_589_934_592).

:- multifile iniziale/1, finale/1, applicabile/2, trasforma/3, euristica/2.

% Punto di ingresso
cercaAStar(ListaAzioni) :- cercaAStar(ListaAzioni, _).

cercaAStar(ListaAzioni, CostoTotale) :-
    iniziale(S0),
    euristica(S0, H0),
    F0 is H0,
    a_star_opt([F0-n(S0, [], [S0], 0)], ListaInv, CostoTotale),
    reverse(ListaInv, ListaAzioni).

% Ciclo principale: espande il nodo migliore fino al goal
a_star_opt([_-n(S, AzInv, _, G)|_], AzInv, G) :-
    finale(S), !.

a_star_opt([_-n(S, AzInv, Visitati, G)|RestoFrontiera], ListaAzioni, CostoTotale) :-
    GNuovo is G + 1,
    findall(
        FNuovo-n(SNuovo, [Azione|AzInv], [SNuovo|Visitati], GNuovo),
        (
            applicabile(Azione, S),
            trasforma(Azione, S, SNuovo),
            \+ member(SNuovo, Visitati),
            euristica(SNuovo, HNuovo),
            FNuovo is GNuovo + HNuovo
        ),
        Figli
    ),
    append(Figli, RestoFrontiera, FrontieraDisordinata),
    keysort(FrontieraDisordinata, NuovaFrontiera),
    a_star_opt(NuovaFrontiera, ListaAzioni, CostoTotale).
