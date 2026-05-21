% -------------------------------------------------------------------------
% Motore di ricerca IDA* (commenti e divisori minimali)
% -------------------------------------------------------------------------

:- multifile iniziale/1, finale/1, applicabile/2, trasforma/3, euristica/2.

% Punto di ingresso
cercaIDAStar(ListaAzioni) :-
    iniziale(S0),
    euristica(S0, SogliaIniziale),
    iterazione(S0, SogliaIniziale, [S0], ListaAzioni).

% Itera con soglia crescente fino alla soluzione
iterazione(S0, Soglia, Visitati, ListaAzioni) :-
    dfs_limite(S0, 0, Soglia, Visitati, Soluzione, ProssimaSoglia),
    ( Soluzione \== null -> ListaAzioni = Soluzione ; ProssimaSoglia \== inf, iterazione(S0, ProssimaSoglia, Visitati, ListaAzioni) ).

% Logica di ricerca
dfs_limite(S, _, _, _, [], _) :- finale(S), !.

dfs_limite(S, G, Soglia, _, null, F) :-
    euristica(S, H),
    F is G + H,
    F > Soglia, !.

dfs_limite(S, G, Soglia, Visitati, Azioni, ProssimoF) :-
    findall(A-SNuovo, (applicabile(A, S), trasforma(A, S, SNuovo), \+ member(SNuovo, Visitati)), Successori),
    GNuovo is G + 1,
    esplora_successori(Successori, GNuovo, Soglia, Visitati, Azioni, ProssimoF).

% Esplorazione sequenziale dei successori
esplora_successori([], _, _, _, null, inf).

esplora_successori([Azione-SNuovo|Altri], G, Soglia, Visitati, Azioni, ProssimoF) :-
    dfs_limite(SNuovo, G, Soglia, [SNuovo|Visitati], SolFiglio, FFiglio),
    ( SolFiglio \== null -> Azioni = [Azione|SolFiglio], ProssimoF = _ ; esplora_successori(Altri, G, Soglia, Visitati, AzioniAltri, FAltri), Azioni = AzioniAltri, scegli_minimo(FFiglio, FAltri, ProssimoF) ).

% Selezione del minimo con supporto a 'inf'
scegli_minimo(inf, F2, F2) :- !.
scegli_minimo(F1, inf, F1) :- !.
scegli_minimo(F1, F2, F1) :- F1 =< F2, !.
scegli_minimo(_, F2, F2).
