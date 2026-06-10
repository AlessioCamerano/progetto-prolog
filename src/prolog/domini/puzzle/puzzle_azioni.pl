% -------------------------------------------------------------------------
% Azioni dell' 8-puzzle
% -------------------------------------------------------------------------

applicabile(su, Stato)       :- nth0(Pos, Stato, 0), Pos > 2.
applicabile(giu, Stato)      :- nth0(Pos, Stato, 0), Pos < 6.
applicabile(sinistra, Stato) :- nth0(Pos, Stato, 0), Pos mod 3 > 0.
applicabile(destra, Stato)   :- nth0(Pos, Stato, 0), Pos mod 3 < 2.

trasforma(su, S, S1)       :- nth0(P, S, 0), P1 is P - 3, scambia(S, P, P1, S1).
trasforma(giu, S, S1)      :- nth0(P, S, 0), P1 is P + 3, scambia(S, P, P1, S1).
trasforma(sinistra, S, S1) :- nth0(P, S, 0), P1 is P - 1, scambia(S, P, P1, S1).
trasforma(destra, S, S1)   :- nth0(P, S, 0), P1 is P + 1, scambia(S, P, P1, S1).

scambia(L, I1, I2, L2) :- nth0(I1, L, E1), nth0(I2, L, E2), set_at(L, I1, E2, LTmp), set_at(LTmp, I2, E1, L2).

set_at([_|T], 0, X, [X|T]).
set_at([H|T], I, X, [H|R]) :- I > 0, I1 is I - 1, set_at(T, I1, X, R).
