import random
import os

SEMI = ['coppe', 'denari', 'spade', 'bastoni']
NUMERI = list(range(1, 11))

PUNTI_PRIMIERA = {7: 21, 6: 18, 1: 16, 5: 15, 4: 14, 3: 13, 2: 12, 8: 10, 9: 10, 10: 10}

class Carta:
    def __init__(self, seme, numero):
        self.seme = seme
        self.numero = numero

    def __repr__(self):
        nome_carta = {
            1: 'Asso',
            2: 'Due',
            3: 'Tre',
            4: 'Quattro',
            5: 'Cinque',
            6: 'Sei',
            7: 'Sette',
            8: 'Fante',
            9: 'Cavallo',
            10: 'Re'
        }
        return f"{nome_carta[self.numero]} di {self.seme}"

    def __eq__(self, other):
        return self.seme == other.seme and self.numero == other.numero

    def __hash__(self):
        return hash((self.seme, self.numero))

    @property
    def image_url(self):
        # Usa percorso relativo e nomi file consistenti
        base_dir = os.path.dirname(os.path.abspath(__file__))
        nome_file = f"{self.seme}{self.numero}.png"
        return os.path.join(base_dir, "cards", nome_file)

def crea_mazzo():
    return [Carta(seme, numero) for seme in SEMI for numero in NUMERI]

def trova_combinazioni(possibili, somma):
    risultati = []

    def backtrack(start, path, totale):
        if totale == somma:
            risultati.append(list(path))
            return
        if totale > somma:
            return
        for i in range(start, len(possibili)):
            path.append(possibili[i])
            backtrack(i + 1, path, totale + possibili[i].numero)
            path.pop()

    backtrack(0, [], 0)
    return risultati

def calcola_primiera(carte):
    punti_per_seme = {}
    for seme in SEMI:
        carte_seme = [c for c in carte if c.seme == seme]
        if not carte_seme:
            punti_per_seme[seme] = 0
            continue
        punti = max(PUNTI_PRIMIERA.get(c.numero, 0) for c in carte_seme)
        punti_per_seme[seme] = punti
    return sum(punti_per_seme.values())

def mossa_ai(mano_ai, tavolo):
    best_mossa = None
    best_presa = []
    for carta in mano_ai:
        combinazioni = trova_combinazioni(tavolo, carta.numero)
        if combinazioni:
            presa = max(combinazioni, key=lambda c: len(c))
            if len(presa) > len(best_presa):
                best_presa = presa
                best_mossa = carta
    if best_mossa:
        mano_ai.remove(best_mossa)
        for c in best_presa:
            tavolo.remove(c)
        scopa = len(tavolo) == 0
        return best_mossa, best_presa, scopa
    else:
        carta = random.choice(mano_ai)
        mano_ai.remove(carta)
        tavolo.append(carta)
        return carta, [], False

class ScopaGame:
    def __init__(self):
        self.mazzo = crea_mazzo()
        random.shuffle(self.mazzo)
        self.mano_giocatore = [self.mazzo.pop() for _ in range(3)]
        self.mano_ai = [self.mazzo.pop() for _ in range(3)]
        self.tavolo = [self.mazzo.pop() for _ in range(4)]
        self.prese_giocatore = []
        self.prese_ai = []
        self.scope_giocatore = 0
        self.scope_ai = 0
        self.ultimo_presa = 'ai'
        self.fine = False

    def mano_giocatore_str(self):
        return '\n'.join(f"{i+1}: {c}" for i, c in enumerate(self.mano_giocatore))

    def tavolo_str(self):
        return ', '.join(str(c) for c in self.tavolo)

    def gioca_carta_giocatore(self, indice):
        if indice < 0 or indice >= len(self.mano_giocatore):
            return ["Scelta non valida."]
        carta_giocata = self.mano_giocatore.pop(indice)
        combinazioni = trova_combinazioni(self.tavolo, carta_giocata.numero)
        messaggi = []
        if combinazioni:
            presa = max(combinazioni, key=lambda c: len(c))
            for c in presa:
                self.tavolo.remove(c)
            self.prese_giocatore.extend(presa)
            self.prese_giocatore.append(carta_giocata)
            messaggi.append(f"Hai preso: {', '.join(str(c) for c in presa)} con {carta_giocata}")
            if len(self.tavolo) == 0:
                self.scope_giocatore += 1
                messaggi.append("Hai fatto una SCOPA!")
            self.ultimo_presa = 'giocatore'
        else:
            self.tavolo.append(carta_giocata)
            messaggi.append(f"Hai messo sul tavolo: {carta_giocata}")
        return messaggi

    def gioca_turno_ai(self):
        carta_ai, presa_ai, scopa_ai = mossa_ai(self.mano_ai, self.tavolo)
        messaggi = []
        if presa_ai:
            self.prese_ai.extend(presa_ai)
            self.prese_ai.append(carta_ai)
            messaggi.append(f"Totti ha preso: {', '.join(str(c) for c in presa_ai)} con {carta_ai}")
            if scopa_ai:
                self.scope_ai += 1
                messaggi.append("Tottti ha fatto una SCOPA!")
            self.ultimo_presa = 'Totti'
        else:
            messaggi.append(f"Totti ha messo sul tavolo: {carta_ai}")
        return messaggi

    def pesca_carte(self):
        if len(self.mazzo) >= 6:
            self.mano_giocatore.extend([self.mazzo.pop() for _ in range(3)])
            self.mano_ai.extend([self.mazzo.pop() for _ in range(3)])

    def partita_finita(self):
        return len(self.mano_giocatore) == 0 and len(self.mano_ai) == 0 and len(self.mazzo) == 0

    def assegna_carte_finali(self):
        if self.ultimo_presa == 'giocatore':
            self.prese_giocatore.extend(self.tavolo)
        else:
            self.prese_ai.extend(self.tavolo)
        self.tavolo.clear()

    def calcola_punti(self):
        punti_giocatore = 0
        punti_ai = 0

        # Punto per più carte
        if len(self.prese_giocatore) > len(self.prese_ai):
            punti_giocatore += 1
        elif len(self.prese_ai) > len(self.prese_giocatore):
            punti_ai += 1

        # Settebello
        settebello = Carta('denari', 7)
        if settebello in self.prese_giocatore:
            punti_giocatore += 1
        elif settebello in self.prese_ai:
            punti_ai += 1

        # Primiera
        primiera_giocatore = calcola_primiera(self.prese_giocatore)
        primiera_ai = calcola_primiera(self.prese_ai)
        if primiera_giocatore > primiera_ai:
            punti_giocatore += 1
        elif primiera_ai > primiera_giocatore:
            punti_ai += 1

        # Scope
        punti_giocatore += self.scope_giocatore
        punti_ai += self.scope_ai

        return punti_giocatore, punti_ai