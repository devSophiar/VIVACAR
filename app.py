from flask import Flask, render_template, redirect, url_for, request, flash
from datetime import datetime , date
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
app = Flask(__name__)

#Configurações
app.config['SECRET_KEY'] = 'chave_secreta_pinkdrive_2025' # para sessões e flash messages
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vivacar.db' # Cria o arquivo do banco na pasta
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # Se algm tentar acessar pag restrita, vai pro login

# Modelo do Banco de Dados (tbl de usuarios)
class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cpf = db.Column(db.String(20), unique=True, nullable=True) 
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha_hash = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(20), nullable=False) # 'funcionario' ou 'cliente'
    locacoes = db.relationship('Locacao', backref='cliente', lazy=True)

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def checar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)
    

# tbl de Carros
class Carro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    modelo = db.Column(db.String(100), nullable=False)
    placa = db.Column(db.String(20), unique=True, nullable=False)
    grupo = db.Column(db.String(50), nullable=True)
    ano = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='Disponivel') 
    valor_diaria = db.Column(db.Float, nullable=True)
    foto_url = db.Column(db.String(500), nullable=True)
    locacoes = db.relationship('Locacao', backref='carro', lazy=True)

class Locacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    carro_id = db.Column(db.Integer, db.ForeignKey('carro.id'), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_devolucao_prevista = db.Column(db.Date, nullable=False)
    km_inicio = db.Column(db.Integer, nullable=True)
    preco_total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Ativa')
    data_devolucao_real = db.Column(db.Date, nullable=True)
    km_final = db.Column(db.Integer, nullable=True)
    diarias_final = db.Column(db.Integer, nullable=True) # 
    valor_final = db.Column(db.Float, nullable=True) # 
    obs = db.Column(db.Text, nullable=True) #


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

#  funcao que cria o banco e o funcionario padrao
def inicializar_banco():
    with app.app_context():
        db.create_all()
        # Verifica se o funcionario padrao já existe 
        func = Usuario.query.filter_by(email='vivacar@gmail.com').first()
        if not func:
            print("Criando funcionário padrão...")
            novo_func = Usuario(
                email='vivacar@gmail.com', 
                tipo='funcionario',
                cpf='000.000.000-00' 
            )
            novo_func.set_senha('funcionarioviva1')
            db.session.add(novo_func)
            db.session.commit()

#Rotas de Autenticação
@app.route('/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # se ja estiver logado, vai pra home correta
        if current_user.tipo == 'funcionario':
            return redirect(url_for('func_home'))
        else:
            return redirect(url_for('cli_home'))

    if request.method == 'POST':
        login_input = request.form.get('login_identificador')
        senha = request.form.get('senha')
        usuario = Usuario.query.filter((Usuario.email == login_input) | (Usuario.cpf == login_input)).first()

        if usuario and usuario.checar_senha(senha):
            login_user(usuario)
            if usuario.tipo == 'funcionario':
                return redirect(url_for('func_home'))
            else:
                return redirect(url_for('cli_home'))
        else:
            flash('Dados incorretos. Verifique e tente novamente.', 'erro')

    return render_template('login.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        cpf = request.form.get('cpf')
        email = request.form.get('email')
        senha = request.form.get('senha')

        # verifica se já existe
        usuario_existente = Usuario.query.filter((Usuario.email == email) | (Usuario.cpf == cpf)).first()
        if usuario_existente:
            flash('Usuário já cadastrado com este E-mail ou CPF.', 'erro')
        else:
            # cria novo cliente
            novo_cliente = Usuario(cpf=cpf, email=email, tipo='cliente')
            novo_cliente.set_senha(senha)
            db.session.add(novo_cliente)
            db.session.commit()
            flash('Conta criada com sucesso! Faça login.', 'sucesso')
            return redirect(url_for('login'))

    return render_template('cadastro.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Rotas do funcionario
@app.route('/funcionario/home')
@login_required
def func_home():
    if current_user.tipo != 'funcionario': return redirect(url_for('cli_home'))
    return render_template('func_home.html', page='home')

@app.route('/funcionario/clientes')
@login_required
def func_clientes():
    if current_user.tipo != 'funcionario': return redirect(url_for('cli_home'))
    lista_clientes = Usuario.query.filter_by(tipo='cliente').all()
    return render_template('func_clientes.html', page='clientes', clientes=lista_clientes)

@app.route('/funcionario/adicionar_cliente', methods=['POST'])
@login_required
def adicionar_cliente():
    if current_user.tipo != 'funcionario': return redirect(url_for('cli_home'))
    cpf = request.form.get('cpf')
    email = request.form.get('email')
    senha = request.form.get('senha')

    # Verifica se já existe
    usuario_existente = Usuario.query.filter((Usuario.email == email) | (Usuario.cpf == cpf)).first()
    
    if usuario_existente:
        flash('Erro: Já existe um cliente com este Email ou CPF.', 'erro')
    else:
        novo_cliente = Usuario(cpf=cpf, email=email, tipo='cliente')
        novo_cliente.set_senha(senha)
        db.session.add(novo_cliente)
        db.session.commit()
        flash('Cliente adicionado com sucesso!', 'sucesso')
    return redirect(url_for('func_clientes'))


@app.route('/funcionario/editar_cliente/<int:id>', methods=['POST'])
@login_required
def editar_cliente(id):
    if current_user.tipo != 'funcionario': return redirect(url_for('cli_home'))
    usuario = Usuario.query.get_or_404(id)
    usuario.email = request.form.get('email')
    usuario.cpf = request.form.get('cpf')

    nova_senha = request.form.get('senha')
    if nova_senha:
        usuario.set_senha(nova_senha)
    try:
        db.session.commit()
        flash('Dados atualizados com sucesso!', 'sucesso')
    except:
        db.session.rollback()
        flash('Erro ao atualizar. Email ou CPF já existem.', 'erro')
        
    return redirect(url_for('func_clientes'))

@app.route('/funcionario/excluir_cliente/<int:id>')
@login_required
def excluir_cliente(id):
    if current_user.tipo != 'funcionario': return redirect(url_for('cli_home'))
    usuario = Usuario.query.get_or_404(id)
    try:
        db.session.delete(usuario)
        db.session.commit()
        flash('Cliente excluído com sucesso.', 'sucesso')
    except:
        flash('Erro ao excluir cliente.', 'erro')
        
    return redirect(url_for('func_clientes'))


@app.route('/funcionario/adicionar_carro', methods=['POST'])
@login_required
def adicionar_carro():
    if current_user.tipo != 'funcionario': return redirect(url_for('cli_home'))
    placa = request.form.get('placa')
    modelo = request.form.get('modelo')
    grupo = request.form.get('grupo')
    ano = request.form.get('ano')
    valor_diaria = request.form.get('valor_diaria', type=float) 
    foto_url = request.form.get('foto_url')
    carro_existente = Carro.query.filter_by(placa=placa).first()
    
    if carro_existente:
        flash(f'Erro: A placa {placa} já está cadastrada.', 'erro')
    else:
        novo_carro = Carro(
            placa=placa,
            modelo=modelo,
            grupo=grupo,
            ano=ano,
            valor_diaria=valor_diaria,
            foto_url=foto_url,         
            status='Disponivel' 
        )
        db.session.add(novo_carro)
        db.session.commit()
        flash('Carro adicionado com sucesso!', 'sucesso')
    return redirect(url_for('func_carros'))


@app.route('/funcionario/editar_carro/<int:id>', methods=['POST'])
@login_required
def editar_carro(id):
    if current_user.tipo != 'funcionario': return redirect(url_for('cli_home'))
    carro = Carro.query.get_or_404(id)
    
    # pega os dados do formulário
    carro.modelo = request.form.get('modelo')
    carro.placa = request.form.get('placa')
    carro.grupo = request.form.get('grupo')
    carro.ano = request.form.get('ano', type=int)
    carro.valor_diaria = request.form.get('valor_diaria', type=float)
    carro.foto_url = request.form.get('foto_url')
    
    try:
        db.session.commit()
        flash('Carro atualizado com sucesso!', 'sucesso')
    except Exception as e:
        db.session.rollback()
        # Erro se a placa ja exsistir
        flash(f'Erro ao atualizar. Verifique se a placa já existe.', 'erro')
        
    return redirect(url_for('func_carros'))

@app.route('/funcionario/excluir_carro/<int:id>')
@login_required
def excluir_carro(id):
    if current_user.tipo != 'funcionario': return redirect(url_for('cli_home'))
    carro = Carro.query.get_or_404(id)
    try:
        db.session.delete(carro)
        db.session.commit()
        flash('Carro excluído com sucesso.', 'sucesso')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao excluir carro. Verifique se ele não está em uma locação ativa.', 'erro')
        
    return redirect(url_for('func_carros'))


@app.route('/funcionario/carros')
@login_required
def func_carros():
    if current_user.tipo != 'funcionario': return redirect(url_for('cli_home'))
    lista_carros = Carro.query.order_by(Carro.modelo).all()
    return render_template('func_carros.html', page='carros', carros=lista_carros)


@app.route('/funcionario/locacoes')
@login_required
def func_locacoes():
    if current_user.tipo != 'funcionario': return redirect(url_for('cli_home'))
    # Busca dados para a tabela
    lista_locacoes = Locacao.query.filter_by(status='Ativa').all()
    # Busca dados para adicionar
    lista_clientes = Usuario.query.filter_by(tipo='cliente').all()
    lista_carros = Carro.query.filter_by(status='Disponivel').all()

    return render_template('func_locacoes.html', page='locacoes', locacoes=lista_locacoes, clientes=lista_clientes, carros_disponiveis=lista_carros)


@app.route('/funcionario/adicionar_locacao', methods=['POST'])
@login_required
def adicionar_locacao():
    if current_user.tipo != 'funcionario': return redirect(url_for('cli_home'))
    try:
        # pega os ids do formulário
        cliente_id = request.form.get('cliente_id')
        carro_id = request.form.get('carro_id')

        # datas de string para 'date'
        data_inicio_str = request.form.get('data_inicio')
        data_fim_str = request.form.get('data_fim')
        data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        km_inicio = request.form.get('km_inicio', type=int)
        carro = Carro.query.get(carro_id)
        
        if not carro or carro.status != 'Disponivel':
            flash('Erro: Carro não está disponível para locação.', 'erro')
            return redirect(url_for('func_locacoes'))
        
        #  calculo de preco no Backend
        dias = (data_fim - data_inicio).days
        if dias <= 0:
            dias = 1
        preco_calculado = dias * carro.valor_diaria

        # cria a locacao
        nova_locacao = Locacao(
            cliente_id=cliente_id,
            carro_id=carro_id,
            data_inicio=data_inicio,
            data_devolucao_prevista=data_fim,
            km_inicio=km_inicio,
            preco_total=preco_calculado,
            status='Ativa'
        )
        # muda statsu carro
        carro.status = 'Locado'
        db.session.add(nova_locacao)
        db.session.add(carro) 
        db.session.commit()
        flash('Locação registrada com sucesso!', 'sucesso')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar locação: {e}', 'erro')
    return redirect(url_for('func_locacoes'))


@app.route('/funcionario/finalizar_devolucao/<int:locacao_id>', methods=['POST'])
@login_required
def finalizar_devolucao(locacao_id):
    if current_user.tipo != 'funcionario': return redirect(url_for('cli_home'))

    try:
        locacao = Locacao.query.get_or_404(locacao_id)

        #Pega dados do formulario
        data_devolucao_str = request.form.get('data_devolucao_real')
        data_real = datetime.strptime(data_devolucao_str, '%Y-%m-%d').date()
        km_final = request.form.get('km_final', type=int)
        obs = request.form.get('obs')

        # calcular dias e preço final
        dias_reais = (data_real - locacao.data_inicio).days

        if dias_reais <= 0:
            dias_reais = 1 # Mínimo de 1 diária
        valor_final_calculado = dias_reais * locacao.carro.valor_diaria

        # Atualiza a locação
        locacao.status = 'Finalizada'
        locacao.data_devolucao_real = data_real
        locacao.km_final = km_final
        locacao.obs = obs
        locacao.diarias_final = dias_reais
        locacao.valor_final = valor_final_calculado

        #  Atualiza carro
        carro = locacao.carro
        carro.status = 'Disponivel'
        db.session.add(locacao)
        db.session.add(carro)
        db.session.commit()

        flash('Devolução registrada com sucesso!', 'sucesso')
        # volta p/devolucoes

        return redirect(url_for('func_devolucoes'))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar devolução: {e}', 'erro')

        return redirect(url_for('func_locacoes'))



@app.route('/funcionario/devolucoes')
@login_required
def func_devolucoes():
    if current_user.tipo != 'funcionario': return redirect(url_for('cli_home'))
    
    # procura as locações finalizadas
    lista_devolucoes = Locacao.query.filter_by(status='Finalizada') \
    .order_by(Locacao.data_devolucao_real.desc()) \
    .all()
    return render_template('func_devolucoes.html', page='devolucoes', devolucoes=lista_devolucoes)



#Rotas do Cliente
@app.route('/cliente/home')
@login_required
def cli_home():
    if current_user.tipo != 'cliente': return redirect(url_for('func_home'))
    return render_template('cli_home.html', page='home', nome=current_user.email)


@app.route('/cliente/reservas')
@login_required
def cli_reservas():
    if current_user.tipo != 'cliente': return redirect(url_for('func_home'))

    # Busca todas as locações do cliente logado
    # ordena pelas ativas primeiro, e depois pela data mais recente.
    lista_locacoes = Locacao.query.filter_by(cliente_id=current_user.id) \
    .order_by(Locacao.status.asc(), Locacao.data_inicio.desc()) \
    .all()
    # Separa as listas para a pagina
    ativas = [loc for loc in lista_locacoes if loc.status == 'Ativa']
    finalizadas = [loc for loc in lista_locacoes if loc.status == 'Finalizada']
    # Passa as listas para a pagina
    return render_template('cli_reservas.html', page='reservas', ativas=ativas, finalizadas=finalizadas)

if __name__ == '__main__':
    inicializar_banco() 
    app.run(debug=True)