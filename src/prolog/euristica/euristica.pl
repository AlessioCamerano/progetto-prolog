% -------------------------------------------------------------------------
% Euristiche (commenti e divisori minimali)
% -------------------------------------------------------------------------

:- multifile finale/1.

% Generale: sceglie il goal più vicino tra tutti i `finale/1`
euristica(Stato, H) :-
    findall(H1, costo_a_un_goal(Stato, H1), Costi),
    min_list(Costi, H).

% Labirinto (Manhattan)
costo_a_un_goal(pos(R, C), H) :-
    finale(pos(RF, CF)),
    H is abs(R - RF) + abs(C - CF).

% Distanza di Manhattan per l'8-puzzle
costo_a_un_goal(Stato, H) :-
    is_list(Stato),
    finale(StatoFinale),
    manhattan_puzzle(Stato, StatoFinale, 0, H).

manhattan_puzzle([], _, _, 0).
manhattan_puzzle([0|T], Finale, Idx, H) :- !, ProssimoIdx is Idx + 1, manhattan_puzzle(T, Finale, ProssimoIdx, H).
manhattan_puzzle([Tessera|T], Finale, Idx, H) :-
    nth0(IdxFinale, Finale, Tessera),
    R_Attuale is Idx // 3, C_Attuale is Idx mod 3,
    R_Finale is IdxFinale // 3, C_Finale is IdxFinale mod 3,
    Dist is abs(R_Attuale - R_Finale) + abs(C_Attuale - C_Finale),
    ProssimoIdx is Idx + 1,
    manhattan_puzzle(T, Finale, ProssimoIdx, H_Restante),
    H is Dist + H_Restante.