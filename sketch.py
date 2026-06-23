import math
import random

# =============================================================================
# ESTADO GERAL (BRAÇO, LABIRINTO E JOGO)
# =============================================================================

# Dicionário que representa o braço robótico articulado.
# Cada segmento tem um comprimento (L1, L2, L3) e um ângulo de rotação (theta).
# Os ângulos são usados na cinemática direta para calcular a posição das juntas.
# 'selecionada' indica qual articulação está ativa para controle.
# 'direcao_rot' inverte o sentido de rotação dependendo do lado de spawn.
braco = {
    'origem': [40, 610],       # ponto fixo no "ombro" do braço (ancora na tela)
    'L1': 200, 'L2': 150, 'L3': 80,  # comprimentos iniciais dos segmentos
    'theta1': -math.pi / 2,    # ângulo absoluto do segmento 1 (em radianos)
    'theta2': math.pi * 0.85,  # ângulo relativo ao segmento anterior
    'theta3': -math.pi * 0.75,
    'vida': 100,
    'selecionada': 0,           # índice da articulação selecionada (0, 1 ou 2)
    'ultimo_dano': -100,        # frame em que ocorreu o último dano (evita dano contínuo)
    'direcao_rot': 1            # multiplicador de direção: +1 ou -1
}

# Representa o objetivo do jogo — o "núcleo" que a garra deve tocar para vencer.
nucleo = {'x': 0, 'y': 0, 'r': 25}

# Robô inimigo que patrulha o labirinto aleatoriamente.
# 'r' é o raio usado tanto para desenho quanto para detecção de colisão.
# 'intervalo' define quantos frames até trocar de direção espontaneamente.
robo = {
    'x': 300, 'y': 350, 'r': 12,
    'angulo': 0, 'vel': 1.2,
    'timer': 0, 'intervalo': 60
}

obstaculos = []   # lista de obstáculos gerados proceduralmente
particulas = []   # lista de partículas ativas no sistema de partículas
estado_jogo = 'JOGANDO'  # pode ser 'JOGANDO', 'VITORIA' ou 'GAME_OVER'

# =============================================================================
# GERAÇÃO PROCEDURAL GEOMÉTRICA
# =============================================================================

def gerar_labirinto():
    """
    Gera um novo labirinto proceduralmente a cada partida.
    
    Conceito de CG: geração procedural usa parâmetros aleatórios controlados
    para criar conteúdo variado sem precisar de assets manuais. Aqui usamos
    restrições de distância para garantir que o labirinto sempre seja jogável
    (sem obstáculos bloqueando a origem ou o núcleo).
    """
    global obstaculos, estado_jogo, particulas
    obstaculos = []
    particulas = []
    estado_jogo = 'JOGANDO'

    # Quatro cantos possíveis de spawn. O braço nasce em um canto,
    # e o núcleo nasce no canto oposto (via ranges 'nx'/'ny').
    opcoes_spawn = [
        {'origem': [40, 610],  'theta1': -math.pi / 4,      'nx': (490, 590), 'ny': (140, 220), 'direcao_rot': 1},
        {'origem': [40, 120],  'theta1':  math.pi / 4,      'nx': (490, 590), 'ny': (490, 580), 'direcao_rot': 1},
        {'origem': [610, 120], 'theta1':  math.pi * 3 / 4,  'nx': (60, 160),  'ny': (490, 580), 'direcao_rot': -1},
        {'origem': [610, 610], 'theta1': -math.pi * 3 / 4,  'nx': (60, 160),  'ny': (140, 220), 'direcao_rot': -1},
    ]
    spawn = random.choice(opcoes_spawn)

    # Aplica o spawn escolhido ao estado do braço
    braco['origem'] = spawn['origem']
    braco['theta1'] = spawn['theta1']
    braco['direcao_rot'] = spawn['direcao_rot']
    braco['theta2'], braco['theta3'] = math.pi * 0.85, -math.pi * 0.75
    braco['L1'], braco['L2'], braco['L3'] = 100, 80, 50
    braco['vida'] = 100
    braco['ultimo_dano'] = -100
    braco['selecionada'] = 0
    
    # Núcleo nasce no quadrante oposto ao braço
    nucleo['x'] = random.uniform(*spawn['nx'])
    nucleo['y'] = random.uniform(*spawn['ny'])
    
    tipos_disponiveis = ['retangulo', 'circulo', 'losango']
    
    # Cada tipo de obstáculo tem uma cor e um dano associados:
    # vermelho = mais perigoso (20), amarelo = menos perigoso (5)
    cores_disponiveis = [
        ((255, 50, 50), 20),
        ((255, 120, 0), 10),
        ((255, 220, 0), 5)
    ]
    
    # Tentamos gerar 16 obstáculos com até 800 tentativas no total.
    # A cada tentativa checamos três restrições espaciais para garantir
    # que o campo seja navegável: distância da origem, do núcleo e de outros obstáculos.
    tentativas = 0
    while len(obstaculos) < 16 and tentativas < 800:
        tentativas += 1
        tipo = random.choice(tipos_disponiveis)
        
        # Círculos têm w == h; retângulos e losangos têm dimensões independentes
        if tipo == 'circulo':
            w = random.uniform(30, 80)
            h = w
        else:
            w = random.uniform(30, 120)
            h = random.uniform(30, 120)
            
        cx = random.uniform(40 + w/2, 610 - w/2)
        cy = random.uniform(120 + h/2, 610 - h/2)
        
        # Garante corredor livre ao redor da origem do braço
        if dist(cx, cy, braco['origem'][0], braco['origem'][1]) < 180 + max(w, h)/2:
            continue
        # Garante corredor livre ao redor do núcleo
        if dist(cx, cy, nucleo['x'], nucleo['y']) < nucleo['r'] + 60 + max(w, h)/2:
            continue
            
        # Verifica sobreposição com obstáculos já existentes usando AABB expandida
        sobreposicao = False
        for obs in obstaculos:
            dist_x = abs(cx - obs['cx'])
            dist_y = abs(cy - obs['cy'])
            min_dist_x = (w + obs['w']) / 2 + 50  # margem extra de 50px entre obstáculos
            min_dist_y = (h + obs['h']) / 2 + 50
            if dist_x < min_dist_x and dist_y < min_dist_y:
                sobreposicao = True
                break
                
        if not sobreposicao:
            cor_escolhida, dano_escolhido = random.choice(cores_disponiveis)
            obstaculos.append({
                'cx': cx, 'cy': cy, 'w': w, 'h': h, 
                'tipo': tipo, 'cor': cor_escolhida, 'dano': dano_escolhido
            })

    iniciar_robo()

# =============================================================================
# ROBÔ INIMIGO
# =============================================================================

def robo_colide_obs(nx, ny):
    """
    Verifica se a posição (nx, ny) do robô colide com paredes ou obstáculos.
    
    Expande cada obstáculo pelo raio do robô (Minkowski sum simplificada):
    ao invés de testar círculo-vs-forma, testamos ponto-vs-forma-expandida.
    Isso é uma técnica comum em jogos para simplificar a detecção de colisão
    entre um círculo e formas arbitrárias.
    """
    r = robo['r']
    # Paredes do labirinto (bordas da área de jogo)
    if nx < 20 + r or nx > 630 - r or ny < 100 + r or ny > 630 - r:
        return True
    for obs in obstaculos:
        w, h, cx, cy = obs['w'], obs['h'], obs['cx'], obs['cy']
        # Retângulo: expande os limites pelo raio r em todas as direções
        if obs['tipo'] == 'retangulo':
            if cx - w/2 - r < nx < cx + w/2 + r and cy - h/2 - r < ny < cy + h/2 + r:
                return True
        # Círculo: testa distância entre centros vs soma dos raios
        elif obs['tipo'] == 'circulo':
            if dist(nx, ny, cx, cy) < w/2 + r:
                return True
        # Losango: usa a equação da norma L1 (distância de Manhattan normalizada)
        # expandida pelo raio — aproximação razoável para losangos
        elif obs['tipo'] == 'losango':
            if abs(nx - cx) / (w/2 + r) + abs(ny - cy) / (h/2 + r) < 1:
                return True
    return False

def robo_colide_braco(nx, ny, juntas):
    """
    Verifica se o robô em (nx, ny) está dentro do raio de colisão de qualquer
    segmento do braço.
    
    Usa dist_ponto_segmento para calcular a distância mínima do ponto ao
    segmento de reta (não à reta infinita). A margem de +3px dá um buffer
    visual para que o robô não "roce" visivelmente a garra ao desviar.
    """
    espessuras = [12, 8, 4]  # metade = raio visual de cada segmento
    for s in range(3):
        d = dist_ponto_segmento(nx, ny,
                                juntas[s][0], juntas[s][1],
                                juntas[s+1][0], juntas[s+1][1])
        if d < robo['r'] + espessuras[s] / 2 + 3:
            return True
    return False

def iniciar_robo():
    """
    Posiciona o robô em um local aleatório válido: fora dos obstáculos,
    longe da origem do braço e longe do núcleo.
    Tenta até 500 vezes antes de desistir (em mapas muito cheios pode falhar silenciosamente).
    """
    for _ in range(500):
        nx = random.uniform(60, 590)
        ny = random.uniform(140, 610)
        if dist(nx, ny, braco['origem'][0], braco['origem'][1]) < 160:
            continue
        if dist(nx, ny, nucleo['x'], nucleo['y']) < 80:
            continue
        if not robo_colide_obs(nx, ny):
            robo['x'] = nx
            robo['y'] = ny
            robo['angulo'] = random.uniform(0, math.pi * 2)
            robo['timer'] = 0
            robo['intervalo'] = random.randint(40, 100)
            break

def atualizar_robo(juntas, em_movimento):
    """
    Atualiza a posição do robô a cada frame usando um comportamento de
    'wandering' (caminhada aleatória com desvio de obstáculos):
    
    1. Incrementa o timer; ao atingir o intervalo, sorteia nova direção
       (evita que o robô fique parado em cantos por tempo indeterminado).
    2. Calcula a próxima posição candidata.
    3. Se colidir: tenta até 12 direções aleatórias alternativas.
    4. Se a garra estiver em movimento E tocar o robô → GAME_OVER.
    
    O parâmetro 'em_movimento' implementa a regra: garra parada = obstáculo;
    garra se movendo = perigo de morte.
    """
    global estado_jogo
    if estado_jogo != 'JOGANDO':
        return

    robo['timer'] += 1
    if robo['timer'] >= robo['intervalo']:
        robo['angulo'] = random.uniform(0, math.pi * 2)
        robo['timer'] = 0
        robo['intervalo'] = random.randint(40, 100)

    nx = robo['x'] + math.cos(robo['angulo']) * robo['vel']
    ny = robo['y'] + math.sin(robo['angulo']) * robo['vel']

    # Função local que agrega as duas checagens de colisão.
    # Quando a garra está parada, ela é tratada como obstáculo sólido.
    def colide(px, py):
        if robo_colide_obs(px, py):
            return True
        if not em_movimento and robo_colide_braco(px, py, juntas):
            return True
        return False

    if colide(nx, ny):
        # Steering: tenta encontrar uma direção livre em até 12 tentativas
        for _ in range(12):
            robo['angulo'] = random.uniform(0, math.pi * 2)
            nx = robo['x'] + math.cos(robo['angulo']) * robo['vel']
            ny = robo['y'] + math.sin(robo['angulo']) * robo['vel']
            if not colide(nx, ny):
                robo['x'] = nx
                robo['y'] = ny
                robo['timer'] = 0
                break
    else:
        robo['x'] = nx
        robo['y'] = ny

    # Só checa morte por contato quando a garra está se movendo
    if em_movimento:
        espessuras = [12, 8, 4]
        for s in range(3):
            d = dist_ponto_segmento(
                robo['x'], robo['y'],
                juntas[s][0], juntas[s][1],
                juntas[s+1][0], juntas[s+1][1]
            )
            if d < robo['r'] + espessuras[s] / 2:
                emitir_particulas_robo(robo['x'], robo['y'])
                braco['vida'] = 0
                estado_jogo = 'GAME_OVER'
                return

def desenhar_robo():
    """
    Desenha o robô inimigo usando primitivas de CG empilhadas com push/pop matrix.
    
    O padrão push_matrix → translate → desenhar → pop_matrix isola as
    transformações: translate move a origem local para (x,y), e todos os
    círculos e linhas são desenhados em coordenadas locais (relativas ao centro).
    Isso evita cálculos manuais de posição absoluta para cada elemento.
    """
    x, y, r = robo['x'], robo['y'], robo['r']
    push_matrix()
    translate(x, y)

    # Halo de glow: círculo grande semi-transparente (efeito de luminescência)
    no_stroke()
    fill(50, 255, 50, 35)   # verde com alpha baixo = translúcido
    circle(0, 0, r * 3.5)

    # Corpo principal
    fill(20, 160, 20)
    stroke(80, 255, 80)
    stroke_weight(2)
    circle(0, 0, r * 2)

    # Olhos: dois círculos brancos com pupilas pretas
    no_stroke()
    fill(255)
    circle(-r * 0.32, -r * 0.1, r * 0.55)
    circle( r * 0.32, -r * 0.1, r * 0.55)
    fill(10, 10, 10)
    circle(-r * 0.32, -r * 0.1, r * 0.28)
    circle( r * 0.32, -r * 0.1, r * 0.28)

    # Antena: linha + bolinha amarela
    stroke(80, 255, 80)
    stroke_weight(1.5)
    line(0, -r, 0, -r * 1.9)
    no_stroke()
    fill(255, 240, 0)
    circle(0, -r * 2.0, r * 0.38)

    pop_matrix()  # restaura o sistema de coordenadas original

# =============================================================================
# SISTEMA DE PARTÍCULAS
# =============================================================================

def emitir_particulas(x, y, cor, quantidade=16):
    """
    Emite uma explosão de partículas no ponto (x, y).
    
    Sistema de partículas é uma técnica clássica de CG para simular
    fenômenos como fogo, fumaça, faíscas e explosões. Cada partícula
    é um objeto independente com posição, velocidade e tempo de vida.
    A direção é sorteada uniformemente em [0, 2π) para criar um burst radial.
    """
    for _ in range(quantidade):
        angulo = random.uniform(0, math.pi * 2)
        vel = random.uniform(1.5, 5.0)
        vida = random.randint(25, 50)  # tempo de vida em frames
        particulas.append({
            'x': x, 'y': y,
            'vx': math.cos(angulo) * vel,  # componente X da velocidade
            'vy': math.sin(angulo) * vel,  # componente Y da velocidade
            'vida': vida, 'vida_max': vida,
            'tamanho': random.uniform(3, 8),
            'cor': cor
        })

def emitir_particulas_nucleo(x, y):
    """
    Explosão especial ao extrair o núcleo — maior, mais rápida e em tons ciano/branco
    para combinar com a paleta visual do núcleo.
    120 partículas com velocidade até 14 e tamanho até 22px.
    """
    cores_explosao = [
        (0, 255, 255), (255, 255, 255),
        (0, 200, 255), (100, 255, 255), (0, 255, 200),
    ]
    for _ in range(120):
        angulo = random.uniform(0, math.pi * 2)
        vel = random.uniform(2.0, 14.0)
        vida = random.randint(50, 100)
        particulas.append({
            'x': x, 'y': y,
            'vx': math.cos(angulo) * vel,
            'vy': math.sin(angulo) * vel,
            'vida': vida, 'vida_max': vida,
            'tamanho': random.uniform(6, 22),
            'cor': random.choice(cores_explosao)
        })

def emitir_particulas_robo(x, y):
    """
    Explosão ao destruir o robô — idêntica em escala à do núcleo, mas em verde.
    Mesmos parâmetros garante simetria visual entre os dois eventos de impacto.
    """
    cores_explosao = [
        (50, 255, 50), (100, 255, 100),
        (180, 255, 180), (255, 255, 255), (0, 200, 0),
    ]
    for _ in range(120):
        angulo = random.uniform(0, math.pi * 2)
        vel = random.uniform(2.0, 14.0)
        vida = random.randint(50, 100)
        particulas.append({
            'x': x, 'y': y,
            'vx': math.cos(angulo) * vel,
            'vy': math.sin(angulo) * vel,
            'vida': vida, 'vida_max': vida,
            'tamanho': random.uniform(6, 22),
            'cor': random.choice(cores_explosao)
        })

def atualizar_particulas():
    """
    Integração de Euler explícita para física das partículas:
    posição += velocidade (a cada frame).
    
    O fator 0.90 aplica amortecimento (drag): multiplica a velocidade por
    menos de 1 a cada frame, simulando resistência do ar. Sem isso, as
    partículas se moveriam em velocidade constante para sempre.
    Remove partículas cuja vida chegou a zero.
    """
    for p in particulas[:]:  # itera sobre cópia da lista para poder remover durante o loop
        p['x'] += p['vx']; p['y'] += p['vy']
        p['vx'] *= 0.90    # amortecimento horizontal
        p['vy'] *= 0.90    # amortecimento vertical
        p['vida'] -= 1
        if p['vida'] <= 0:
            particulas.remove(p)

def desenhar_particulas():
    """
    Renderiza cada partícula como um círculo cujo tamanho e alpha decaem
    proporcionalmente ao tempo de vida restante (interpolação linear).
    
    'progresso' vai de 1.0 (recém-criada) até ~0 (quase morta), fazendo
    a partícula encolher e desaparecer gradualmente — efeito de fade-out.
    O alpha vai de 255 (opaco) a 0 (transparente), criando dissolução suave.
    """
    no_stroke()
    for p in particulas:
        progresso = p['vida'] / p['vida_max']   # valor em [0, 1]
        r, g, b = p['cor']
        fill(r, g, b, int(255 * progresso))     # alpha proporcional à vida
        circle(p['x'], p['y'], p['tamanho'] * progresso)  # tamanho encolhe

# =============================================================================
# DESENHO DO LABIRINTO
# =============================================================================

def desenhar_forma(tipo, w, h):
    """
    Primitiva de desenho centralizada na origem local (0, 0).
    
    Sempre chamada dentro de um bloco push/translate, então as coordenadas
    são relativas ao centro do obstáculo. Isso permite usar a mesma função
    para qualquer obstáculo independentemente de sua posição na tela.
    
    O losango usa begin_shape/vertex/end_shape — pipeline de vértices manual,
    útil para formas que as primitivas básicas não cobrem.
    """
    if tipo == 'retangulo': 
        rect(-w/2, -h/2, w, h)      # rect começa no canto superior-esquerdo
    elif tipo == 'circulo': 
        circle(0, 0, w)              # circle usa centro + diâmetro
    elif tipo == 'losango':
        begin_shape()
        vertex(0, -h/2)   # topo
        vertex(w/2, 0)    # direita
        vertex(0, h/2)    # base
        vertex(-w/2, 0)   # esquerda
        end_shape(CLOSE)  # fecha conectando último ao primeiro vértice

def desenhar_bordas_labirinto():
    """
    Desenha os quatro retângulos que formam as paredes do labirinto.
    Chamada duas vezes em desenhar_labirinto: uma para o glow (stroke grosso)
    e outra para a linha nítida (stroke fino) — técnica de fake glow duplo.
    """
    rect(0, 80, 650, 20)   # parede superior
    rect(0, 630, 650, 20)  # parede inferior
    rect(0, 80, 20, 570)   # parede esquerda
    rect(630, 80, 20, 570) # parede direita
    
def dist_ponto_segmento(px, py, ax, ay, bx, by):
    """
    Calcula a distância mínima entre o ponto P e o segmento AB.
    
    Conceito de CG: projeção de ponto em segmento. Calculamos o parâmetro
    't' da projeção ortogonal de P sobre a reta AB. Se t ∈ [0,1], o pé
    da perpendicular cai dentro do segmento; senão, usamos o extremo mais
    próximo (A ou B). Isso é fundamental para detecção de colisão com linhas.
    """
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return dist(px, py, ax, ay)  # segmento degenerado: é um ponto
    # t é o parâmetro de projeção, clampado em [0, 1] para ficar no segmento
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return dist(px, py, ax + t * dx, ay + t * dy)

def desenhar_labirinto(juntas):
    """
    Renderiza as bordas e os obstáculos com efeito de glow neon e respiração.
    
    Efeito glow: desenhamos o mesmo shape duas vezes —
      1ª passagem: stroke grosso + transparente (halo difuso)
      2ª passagem: stroke fino + opaco (contorno nítido)
    
    Efeito breathing (respiração): stroke_weight oscila com sin(frame_count * freq),
    criando animação cíclica sem precisar de keyframes.
    
    Efeito de saturação por proximidade: quando o braço se aproxima,
    removemos o canal mínimo de cada cor, tornando-a mais saturada/vibrante.
    Isso dá feedback visual de perigo.
    
    'juntas' é passado para calcular a distância de cada obstáculo ao braço
    inteiro (não só à ponta), usando dist_ponto_segmento em cada segmento.
    """
    # Bordas do labirinto com glow roxo
    fill(12, 16, 22)
    stroke(150, 50, 255, 80); stroke_weight(10)  # halo difuso
    desenhar_bordas_labirinto()
    no_fill()
    stroke(180, 80, 255); stroke_weight(2)        # contorno nítido
    desenhar_bordas_labirinto()
    
    for obs in obstaculos:
        push_matrix()
        translate(obs['cx'], obs['cy'])  # move origem para o centro do obstáculo
        w, h, tipo = obs['w'], obs['h'], obs['tipo']
        cx, cy = obs['cx'], obs['cy']

        # Distância mínima de qualquer segmento do braço ao obstáculo
        d = min(
            dist_ponto_segmento(cx, cy, juntas[0][0], juntas[0][1], juntas[1][0], juntas[1][1]),
            dist_ponto_segmento(cx, cy, juntas[1][0], juntas[1][1], juntas[2][0], juntas[2][1]),
            dist_ponto_segmento(cx, cy, juntas[2][0], juntas[2][1], juntas[3][0], juntas[3][1])
        )

        # Frequência de pulsação aumenta quando o braço está a menos de 150px
        freq = 0.30 if d < 150 else 0.1
        glow_weight = 10 + 6 * math.sin(frame_count * freq)  # oscila entre 4 e 16

        # Aumento de saturação por proximidade: t ∈ [0,1] para d ∈ [50,0]
        r, g, b = obs['cor']
        t = max(0, (50 - d) / 50)   # 0 quando distante, 1 quando dentro de 50px
        if t > 0:
            m = min(r, g, b)         # canal mínimo define o "branco" da cor
            r = int(r - m * t)       # subtrai o mínimo → satura a cor
            g = int(g - m * t)
            b = int(b - m * t)

        # 1ª passagem: fundo escuro + halo colorido semi-transparente
        fill(15, 20, 28); stroke(r, g, b, 80); stroke_weight(glow_weight)
        desenhar_forma(tipo, w, h)
        # 2ª passagem: sem preenchimento + borda nítida
        no_fill(); stroke(r, g, b); stroke_weight(2)
        desenhar_forma(tipo, w, h)
        pop_matrix()

def desenhar_nucleo():
    """
    Desenha o núcleo com efeito de pulsação usando sin(frame_count).
    
    Três camadas concêntricas com alpha decrescente simulam um glow volumétrico:
    círculo externo grande e translúcido → médio semi-opaco → núcleo branco sólido.
    O raio oscila com sin() para criar a animação de "batimento".
    """
    push_matrix()
    translate(nucleo['x'], nucleo['y'])
    pulso = math.sin(frame_count * 0.1) * 8  # oscila ±8px a 0.1 rad/frame

    no_stroke()
    fill(0, 255, 255, 30);  circle(0, 0, (nucleo['r'] * 2) + pulso + 30)  # halo externo
    fill(0, 200, 255, 80);  circle(0, 0, (nucleo['r'] * 2) + pulso + 10)  # halo médio
    fill(255);               circle(0, 0, nucleo['r'] * 1.5)               # núcleo sólido
    pop_matrix()

# =============================================================================
# CINEMÁTICA E INTERAÇÃO DO BRAÇO
# =============================================================================

def calcular_cinematica():
    """
    Implementa cinemática direta (forward kinematics) para um braço de 3 segmentos.
    
    Cinemática direta: dado os ângulos das juntas, calculamos as posições
    cartesianas (x,y) de cada junta e da ponta.
    
    Os ângulos são acumulados: a2 = theta1 + theta2 (relativo ao mundo),
    a3 = theta1 + theta2 + theta3. Isso significa que theta2 e theta3 são
    ângulos relativos ao segmento anterior, não ao eixo global — comportamento
    natural de um braço articulado.
    
    Também calculamos os pontos médios de cada segmento (usados no HUD).
    
    Retorna:
      juntas: lista de 4 pontos [(x0,y0), (x1,y1), (x2,y2), (ponta_x, ponta_y)]
      pontos_medios: lista de 3 pontos no meio de cada segmento
    """
    x0, y0 = braco['origem']
    L1, L2, L3 = braco['L1'], braco['L2'], braco['L3']
    t1, t2, t3 = braco['theta1'], braco['theta2'], braco['theta3']

    # Ângulos absolutos no sistema de coordenadas do mundo
    a1 = t1
    a2 = t1 + t2
    a3 = t1 + t2 + t3

    # Posição de cada junta: ponto_anterior + L * (cos(ângulo), sin(ângulo))
    x1 = x0 + L1 * math.cos(a1); y1 = y0 + L1 * math.sin(a1)
    x2 = x1 + L2 * math.cos(a2); y2 = y1 + L2 * math.sin(a2)
    ponta_x = x2 + L3 * math.cos(a3); ponta_y = y2 + L3 * math.sin(a3)

    # Pontos médios de cada segmento (para uso no HUD e hitbox de clique)
    m1x = x0 + (L1/2)*math.cos(a1); m1y = y0 + (L1/2)*math.sin(a1)
    m2x = x1 + (L2/2)*math.cos(a2); m2y = y1 + (L2/2)*math.sin(a2)
    m3x = x2 + (L3/2)*math.cos(a3); m3y = y2 + (L3/2)*math.sin(a3)

    juntas = [(x0,y0),(x1,y1),(x2,y2),(ponta_x,ponta_y)]
    pontos_medios = [(m1x,m1y),(m2x,m2y),(m3x,m3y)]
    return juntas, pontos_medios

def checar_colisoes_integrais(juntas):
    """
    Detecção de colisão por amostragem integral ao longo de cada segmento.
    
    O problema de testar "segmento vs forma" diretamente é complexo.
    A solução adotada é amostrar N pontos igualmente espaçados ao longo
    de cada segmento e testar cada ponto individualmente — quanto menor
    o passo (6px aqui), mais precisa a detecção.
    
    Para cada ponto amostrado, verificamos:
      1. Colisão com parede: dano alto (50), ativa flash vermelho
      2. Colisão com obstáculo: dano conforme o tipo (5, 10 ou 20)
    
    O cooldown de 30 frames entre danos evita que um único contato
    drene toda a vida de uma vez (invulnerabilidade temporária).
    """
    global estado_jogo
    if estado_jogo != 'JOGANDO' or frame_count < braco['ultimo_dano'] + 30:
        return

    for s in range(3):  # itera sobre os 3 segmentos
        p_inicio = juntas[s]; p_fim = juntas[s+1]
        comprimento_haste = dist(p_inicio[0], p_inicio[1], p_fim[0], p_fim[1])
        passos = max(8, int(comprimento_haste / 6))  # 1 amostra a cada 6px

        for step in range(passos + 1):
            t = step / passos  # t ∈ [0, 1] ao longo do segmento
            # Interpolação linear: ponto = inicio + t * (fim - inicio)
            px = p_inicio[0] + t * (p_fim[0] - p_inicio[0])
            py = p_inicio[1] + t * (p_fim[1] - p_inicio[1])

            # Colisão com bordas
            if px <= 20 or px >= 630 or py <= 100 or py >= 630:
                braco['vida'] -= 50
                braco['ultimo_dano'] = frame_count
                emitir_particulas(px, py, (180, 80, 255))
                if braco['vida'] <= 0:
                    braco['vida'] = 0; estado_jogo = 'GAME_OVER'
                return

            # Colisão com cada obstáculo (ponto dentro da forma)
            for obs in obstaculos:
                colidiu = False
                w, h = obs['w'], obs['h']; cx, cy = obs['cx'], obs['cy']
                if obs['tipo'] == 'retangulo':
                    if cx - w/2 <= px <= cx + w/2 and cy - h/2 <= py <= cy + h/2:
                        colidiu = True
                elif obs['tipo'] == 'circulo':
                    if dist(px, py, cx, cy) <= w/2: colidiu = True
                elif obs['tipo'] == 'losango':
                    # Equação da norma L1 normalizada: |x/a| + |y/b| ≤ 1
                    if abs(px-cx)/(w/2) + abs(py-cy)/(h/2) <= 1: colidiu = True
                if colidiu:
                    braco['vida'] -= obs['dano']
                    braco['ultimo_dano'] = frame_count
                    emitir_particulas(px, py, obs['cor'])
                    if braco['vida'] <= 0:
                        braco['vida'] = 0; estado_jogo = 'GAME_OVER'
                    return

def desenhar_segmento(comprimento, espessura, indice):
    """
    Desenha um único segmento do braço no espaço local (origem = junta inicial).
    
    A linha vai de (0,0) até (comprimento, 0) — sempre horizontal no espaço local.
    As rotações acumuladas pelo stack de matrizes (push/rotate) fazem ela
    aparecer no ângulo correto na tela. Isso é o princípio fundamental do
    pipeline de transformações hierárquicas em CG.
    
    O círculo na origem (0,0) representa a junta (articulação). Fica verde
    se selecionada, ciano se não selecionada.
    """
    stroke(200); stroke_weight(espessura)
    line(0, 0, comprimento, 0)      # segmento sempre ao longo do eixo X local
    if braco['selecionada'] == indice:
        fill(50, 255, 50); stroke(255)   # verde = articulação ativa
    else:
        fill(40); stroke(0, 200, 255)    # ciano = articulação inativa
    stroke_weight(max(1, espessura / 4))
    circle(0, 0, espessura * 2.5)    # junta na origem do segmento

def desenhar_braco():
    """
    Desenha o braço completo usando transformações hierárquicas encadeadas.
    
    Conceito central de CG: hierarquia de transformações (scene graph simplificado).
    Cada rotate() gira o sistema local; cada translate() move a origem para
    o final do segmento anterior. O próximo segmento é desenhado relativo
    a essa nova origem. O stack de matrizes (implícito no push/pop) garante
    que as transformações anteriores não vazem.
    
    Exemplo: ao rodar theta2, apenas o segmento 2 e o 3 giram (como num braço real).
    """
    push_matrix()
    translate(braco['origem'][0], braco['origem'][1])  # move para o ombro

    rotate(braco['theta1'])                             # gira para o ângulo do segmento 1
    desenhar_segmento(braco['L1'], 12, 0)
    translate(braco['L1'], 0)                          # avança para o cotovelo

    rotate(braco['theta2'])                             # gira relativo ao segmento 1
    desenhar_segmento(braco['L2'], 8, 1)
    translate(braco['L2'], 0)                          # avança para o pulso

    rotate(braco['theta3'])                             # gira relativo ao segmento 2
    desenhar_segmento(braco['L3'], 4, 2)
    translate(braco['L3'], 0)                          # avança até a ponta

    pop_matrix()  # restaura a matriz original

# =============================================================================
# HUD E TELAS DE FIM
# =============================================================================

def desenhar_hud():
    """
    HUD (Heads-Up Display): camada de interface 2D sobreposta à cena.
    
    Desenhado por cima de tudo no draw() para garantir que nunca fique
    atrás dos elementos do jogo. Usa coordenadas absolutas de tela (não
    é afetado pelas transformações de matriz do braço).
    
    Mostra: controles, articulação ativa, alcance atual e barra de vida.
    A barra de vida é um retângulo cujo comprimento = 1.8 * vida (máx 180px).
    """
    fill(10, 12, 18); no_stroke(); rect(0, 0, 650, 80)   # fundo escuro do HUD
    stroke(150, 50, 255); stroke_weight(3); line(0, 80, 650, 80)  # separador roxo

    fill(0, 255, 255); no_stroke(); text_size(12)
    text("SISTEMA DE MANIPULAÇÃO", 20, 25)

    fill(180, 200, 255); text_size(11)
    text("Articulação: Mouse / [ ↑ ] / [ ↓ ]", 20, 45)
    text("Extensão:   [ + ] / [ - ]", 20, 65)

    nomes_art = ["OMBRO PRIMÁRIO", "COTOVELO", "PULSO / GARRA"]
    tamanho_atual = int(braco[f'L{braco["selecionada"] + 1}'])

    fill(50, 255, 50); text_size(12)
    text(f"MODULO ATIVO: {nomes_art[braco['selecionada']]}", 220, 35)
    text(f"ALCANCE: {tamanho_atual}mm", 220, 55)

    fill(0, 255, 255); text_size(12)
    text("INTEGRIDADE DA GARRA", 440, 25)

    # Barra de vida: fundo escuro + preenchimento vermelho proporcional
    fill(50, 10, 10); stroke(255, 50, 50, 100); stroke_weight(2)
    rect(440, 35, 180, 15)                      # fundo da barra
    no_stroke(); fill(255, 50, 50)
    rect(440, 35, 1.8 * braco['vida'], 15)      # preenchimento (máx 180px para vida=100)

    fill(255); text_size(11)
    text(f"STATUS: {braco['vida']}%", 440, 65)

def desenhar_telas_de_fim():
    """
    Sobrepõe uma tela de fim de jogo semi-transparente quando necessário.
    
    O fundo com alpha (230/255) permite ver as partículas ainda se movendo
    atrás do painel — reforça o impacto visual do evento.
    text_align(CENTER, CENTER) centraliza o texto no ponto de referência,
    que foi transladado para o centro da tela com translate(width/2, height/2).
    """
    if estado_jogo == 'JOGANDO': return

    push_matrix()
    translate(width/2, height/2 + 40)   # centra o painel na tela

    if estado_jogo == 'VITORIA':
        fill(0, 20, 40, 230); stroke(0, 255, 255); stroke_weight(2)
        rect(-220, -60, 440, 120)
        fill(0, 255, 255); text_size(36); text_align(CENTER, CENTER)
        text("NÚCLEO EXTRAÍDO", 0, -15)
        fill(255); text_size(14)
        text("SISTEMA ONLINE. Pressione [ESPAÇO] para reiniciar.", 0, 30)
    elif estado_jogo == 'GAME_OVER':
        fill(40, 0, 0, 230); stroke(255, 50, 50); stroke_weight(2)
        rect(-220, -60, 440, 120)
        fill(255, 50, 50); text_size(36); text_align(CENTER, CENTER)
        text("FALHA CRÍTICA", 0, -15)
        fill(255); text_size(14)
        text("GARRA DESTRUÍDA. Pressione [ESPAÇO] para reiniciar.", 0, 30)

    text_align(LEFT, BASELINE)   # restaura o alinhamento padrão
    pop_matrix()

# =============================================================================
# LOOP DE ENGINE
# =============================================================================

def setup():
    """
    Executado uma única vez ao iniciar o sketch.
    Define o tamanho da janela e gera o primeiro labirinto.
    """
    size(650, 650)
    text_font("Arial", 14)
    gerar_labirinto()

def draw():
    """
    Loop principal: executado ~60 vezes por segundo (60 FPS).
    
    Ordem de renderização (painter's algorithm — fundo para frente):
      1. Grade de fundo (mais atrás)
      2. Labirinto (obstáculos)
      3. Núcleo
      4. Robô
      5. Braço
      6. Partículas (por cima de tudo na cena)
      7. Ponta da garra (marcador vermelho)
      8. Flash de dano (overlay)
      9. HUD (sempre na frente)
      10. Telas de fim (frente de tudo)
    
    'em_movimento' captura se o jogador está pressionando uma tecla de controle
    neste frame exato, e é passado ao robô para decidir seu comportamento.
    """
    global estado_jogo
    background(10, 12, 18)   # limpa o frame anterior (cor de fundo)

    # Grade de pontos decorativa: linhas muito transparentes formam uma malha
    stroke(255, 255, 255, 10); stroke_weight(1)
    for x in range(0, width, 40): line(x, 80, x, height)
    for y in range(80, height, 40): line(0, y, width, y)

    velocidade_rot = 0.02    # radianos por frame para rotação
    velocidade_tam = 2.0     # pixels por frame para extensão

    # Detecta teclas de controle do braço neste frame
    teclas_movimento = ("ArrowUp", "ArrowDown", "+", "=", "-", "_")
    em_movimento = is_key_pressed and estado_jogo == 'JOGANDO' and key in teclas_movimento

    if em_movimento:
        if key == "ArrowUp":
            braco[f'theta{braco["selecionada"] + 1}'] -= velocidade_rot * braco['direcao_rot']
        elif key == "ArrowDown":
            braco[f'theta{braco["selecionada"] + 1}'] += velocidade_rot * braco['direcao_rot']
        elif key == "+" or key == "=":
            chave_L = f'L{braco["selecionada"] + 1}'
            braco[chave_L] = min(braco[chave_L] + velocidade_tam, 350)
        elif key == "-" or key == "_":
            chave_L = f'L{braco["selecionada"] + 1}'
            braco[chave_L] = max(braco[chave_L] - velocidade_tam, 40)

    # Recalcula a cinemática direta com os ângulos atualizados
    juntas, pontos_medios = calcular_cinematica()
    ponta_x, ponta_y = juntas[3]

    # Pipeline de renderização da cena
    desenhar_labirinto(juntas)
    desenhar_nucleo()
    desenhar_robo()
    desenhar_braco()

    checar_colisoes_integrais(juntas)  # verifica se braço bateu em algo
    atualizar_robo(juntas, em_movimento)  # move o robô e checa colisão com garra

    atualizar_particulas()   # integra física das partículas
    desenhar_particulas()    # renderiza partículas vivas

    # Ponta da garra: pequeno círculo vermelho sobre a posição da ponta
    push_matrix()
    translate(ponta_x, ponta_y)
    fill(255, 20, 0); no_stroke(); circle(0, 0, 6)
    pop_matrix()

    # Flash vermelho de dano: overlay transparente por 15 frames após colisão
    if frame_count < braco['ultimo_dano'] + 15:
        fill(255, 0, 0, 80); no_stroke(); rect(0, 80, 650, 570)

    # Condição de vitória: ponta da garra dentro do raio do núcleo
    if estado_jogo == 'JOGANDO' and dist(ponta_x, ponta_y, nucleo['x'], nucleo['y']) < nucleo['r']:
        estado_jogo = 'VITORIA'
        emitir_particulas_nucleo(nucleo['x'], nucleo['y'])

    desenhar_hud()           # HUD sempre por cima da cena
    desenhar_telas_de_fim()  # painéis de fim de jogo (se aplicável)

def mouse_pressed():
    """
    Seleção de articulação por clique: itera de trás para frente (pulso → ombro)
    para que articulações menores/mais à frente tenham prioridade de seleção.
    
    O raio de hitbox é proporcional à espessura visual do segmento, tornando
    articulações maiores mais fáceis de clicar — UX intuitivo.
    """
    if estado_jogo != 'JOGANDO': return
    mx, my = mouse_x, mouse_y
    juntas, _ = calcular_cinematica()
    espessuras = [12, 8, 4]
    for i in range(2, -1, -1):   # do pulso (2) ao ombro (0)
        px, py = juntas[i]       # posição da junta i
        if dist(mx, my, px, py) <= espessuras[i] * 1.25:
            braco['selecionada'] = i; break

def key_pressed():
    """
    Callback de tecla pressionada (evento único, não contínuo como is_key_pressed).
    Espaço reinicia o jogo gerando um novo labirinto.
    """
    if key == ' ':
        gerar_labirinto()