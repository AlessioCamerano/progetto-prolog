% -------------------------------------------------------------------------
% Punto di ingresso principale (intestazione e divisori minimali)
% -------------------------------------------------------------------------

% Carica i motori e i domini dalla nuova struttura a cartelle
:- consult('src/prolog/algoritmi/aStar.pl').
:- consult('src/prolog/algoritmi/idaStar.pl').
:- consult('src/prolog/euristica/euristica.pl').
:- consult('src/prolog/domini/labirinto/labirinto.pl').
:- consult('src/prolog/domini/labirinto/labirinto_azioni.pl').
:- consult('src/prolog/domini/puzzle/puzzle.pl').
:- consult('src/prolog/domini/puzzle/puzzle_azioni.pl').

% --- ESECUZIONE ---
start :-
    write('Scegli l\'algoritmo:'), nl,
    write('1. A* (Standard)'), nl,
    write('2. IDA* (Iterative Deepening)'), nl,
    read(Scelta),
    statistics(runtime, [T0|_]),
    esegui(Scelta),
    statistics(runtime, [T1|_]),
    Tempo is (T1 - T0) / 1000,
    format('Tempo di esecuzione: ~3f secondi~n', [Tempo]),
    stampa_report_memoria.

% Gestione A*
esegui(1) :-
    write('Avvio ricerca A*...'), nl,
    (cercaAStar(Azioni, Costo) -> 
        stampa_successo(Azioni, Costo) ; 
        write('Nessuna soluzione trovata.')), !.

% Gestione IDA*
esegui(2) :-
    write('Avvio ricerca IDA*...'), nl,
    (cercaIDAStar(Azioni) -> 
        length(Azioni, Costo),
        stampa_successo(Azioni, Costo) ; 
        write('Nessuna soluzione trovata.')), !.

esegui(_) :- write('Scelta non valida.'), nl.

% --- UTILITY DI STAMPA E MEMORIA ---

stampa_successo(Azioni, Costo) :-
    nl, write('--- RISULTATI ---'), nl,
    write('Soluzione trovata!'), nl,
    write('Costo: '), write(Costo), nl,
    format('Azioni: ~w~n', [Azioni]).

stampa_report_memoria :-
    % 'stack' restituisce la memoria totale usata dagli stack di Prolog
    statistics(stack, MemStack),
    % 'memory' restituisce la memoria totale del processo
    statistics(memory, [MemProcesso, _]),
    
    MB_Stack is MemStack / 1048576,
    MB_Processo is MemProcesso / 1048576,
    
    nl, write('--- REPORT MEMORIA ---'), nl,
    format('Memoria Stack (Nodi/Dati): ~2f MB~n', [MB_Stack]),
    format('Memoria Totale Processo:   ~2f MB~n', [MB_Processo]),
    write('-----------------------'), nl.