from datetime import datetime, timedelta, date
import unittest
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy import desc, func, extract, inspect
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from flask_jwt_extended.exceptions import NoAuthorizationError, InvalidHeaderError
import testing_api as TEST
import configparser

app = Flask(__name__)

config = configparser.ConfigParser()
config.read('/var/www/html/config.cfg')
app.config['SQLALCHEMY_DATABASE_URI'] = config['DEFAULT']['SQLALCHEMY_DATABASE_URI']
app.config['SECRET_KEY'] = config['DEFAULT']['SECRET_KEY']
app.config['JWT_SECRET_KEY'] = config['DEFAULT']['JWT_SECRET_KEY']
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 3600
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = 604800

jwt = JWTManager(app)
db = SQLAlchemy(app)

# Vytvoření vlastního kontextu
with app.app_context():
    # Automatické mapování na základě existujících tabulek
    Base = automap_base()
    Base.prepare(db.engine, reflect=True)

    # Zde získáváme třídy reprezentující různé tabulky
    AggregatedDailyData = Base.classes.aggregated_daily_data
    AggregatedWeeklyData = Base.classes.aggregated_weekly_data
    AggregatedMonthlyData = Base.classes.aggregated_monthly_data
    AggregatedData = Base.classes.aggregated_data
    BaseMeteostation = Base.classes.Weather_table_meteostation1
    MeteoCodes = Base.classes.meteo_codes
    
    Users = Base.classes.users if 'users' in Base.classes else None
    if Users:
        inspector = inspect(db.engine)
        columns = inspector.get_columns(Users.__table__.name)
        print([column['name'] for column in columns])


#FUNCTIONS
def create_access_token_for_user(user):
    return create_access_token(identity={'username': user.username})

def get_last_data(table_class):
    try:
        last_data = db.session.query(table_class).order_by(desc(table_class.id)).first()
        if last_data:
            result = last_data.__dict__
            result.pop('_sa_instance_state', None)
            return jsonify(result)
        else:
            return jsonify({'message': 'No data found in the table.'})
    except Exception as e:
        return jsonify({'error': str(e)})
        
def get_all_last_data(table_class):
    try:
        # Získání aktuálního data
        current_date = datetime.now().date()

        # Vytvoření časového rozmezí od 00:00:00 do 23:59:59 pro celý den
        start_of_day = datetime.combine(current_date, datetime.min.time())
        end_of_day = datetime.combine(current_date, datetime.max.time())

        # Získání posledních dat z tabulky pro dané časové rozmezí
        last_data = db.session.query(table_class).filter(
            table_class.time.between(start_of_day, end_of_day)
        ).all()

        # Příprava výstupu
        data_list = [row.__dict for row in last_data]
        for item in data_list:
            item.pop('_sa_instance_state', None)

        return jsonify(data_list)

    except Exception as e:
        return jsonify({'error': str(e)})
        
def get_all_columns(table_class):
    inspector = inspect(db.engine)
    columns = inspector.get_columns(table_class.__table__.name)
    all_columns = [column['name'] for column in columns]
    response = {'rows': all_columns}
    return jsonify(response)
   
def get_data_by_columns(table_class, columns=None):
    try:
        # Přidání podmínky pro vybrané sloupce
        if columns:
            selected_columns = columns.split(',')
            data = db.session.query(table_class).with_entities(*[getattr(table_class, column) for column in selected_columns]).all()
            data_list = [row._asdict() for row in data]

            return jsonify(data_list)
        else:
            return jsonify({'message': 'No columns specified.'})
    except Exception as e:
        return jsonify({'error': str(e)})
        
def get_data_by_date_and_column(table_class, date_str=None, time=None, column=None):
    try:
        if date_str:
            date_object = datetime.strptime(date_str, '%Y-%m-%d')
        else:
            date_object = datetime.now()

        # Zjistit název sloupce s datem v tabulce
        if 'date' in table_class.__dict__:
            date_column_name = 'date'
        elif 'week_start' in table_class.__dict__:
            date_column_name = 'week_start'
        elif 'next_month_start' in table_class.__dict__:
            date_column_name = 'next_month_start'
        elif 'time' in table_class.__dict__:
            date_column_name = 'time'
        else:
            raise Exception(f"Tabulka {table_class.__name__} nemá sloupec s datem.")

        # Vytvoření filtrovacího intervalu pro celý den
        start_of_day = datetime.combine(date_object, datetime.min.time())
        end_of_day = datetime.combine(date_object, datetime.max.time())

        # Sestavení filtru na základě názvu sloupce s datem
        filter_condition = {
            date_column_name: (start_of_day, end_of_day)
        }

        if time:
            # Pokud je zadán parametr time, přidáme čas k filtru
            time_object = datetime.strptime(time, '%H:%M:%S').time()
            filter_condition['time'] = time_object

        # Přidání podmínky pro vybraný sloupec
        if column:
            filter_condition_column = {column: True}
            filter_condition.update(filter_condition_column)

        data = db.session.query(table_class).filter(
            *[
                getattr(table_class, k).between(v[0], v[1])
                if isinstance(v, tuple) and len(v) == 2
                else getattr(table_class, k) == v
                for k, v in filter_condition.items()
            ]
        ).all()

        data_list = [row.__dict__ for row in data]
        for item in data_list:
            item.pop('_sa_instance_state', None)
        return jsonify(data_list)
    except Exception as e:
        return jsonify({'error': str(e)})

              
def get_data_by_columns_and_date_test(table_class, date=None, columns=None):
    try:
        # Přidání podmínky pro vybrané sloupce a datum
        if columns:
            selected_columns = columns.split(',')
        else:
            selected_columns = []

        query = db.session.query(table_class)
        if date:
            date_object = datetime.strptime(date, '%Y-%m-%d')
            query = query.filter_by(week_start=date_object)

        if selected_columns:
            # Výběr pouze sloupců, které jsou uvedeny v dotazu
            result = query.with_entities(*[getattr(table_class, column) for column in selected_columns]).all()
        else:
            # Pokud nejsou uvedeny žádné sloupce, vrátíme všechny sloupce
            result = query.all()

        # Převedeme výsledek na seznam slovníků
        data_list = [dict(zip(selected_columns, row)) for row in result] if selected_columns else [row._asdict() for row in result]

        return jsonify(data_list)
    except Exception as e:
        return jsonify({'error': str(e)})

def get_all_data(table_class, column=None):
    try:
        # Přidání podmínky pro vybraný sloupec
        if column:
            data = db.session.query(table_class).filter_by(**{column: True}).all()
        else:
            data = db.session.query(table_class).all()
        data_list = [row.__dict__ for row in data]
        for item in data_list:
            item.pop('_sa_instance_state', None)
        return jsonify(data_list)
    except Exception as e:
        return jsonify({'error': str(e)})
        
def get_meteo_code(code):
    try:
        meteo_code = db.session.query(MeteoCodes).filter_by(code=code).first()
        return meteo_code
    except Exception as e:
        return None
    

def get_all_data_by_date_today(table_class, column=None):
    try:
        date_object = datetime.now().date()

        # Zjistit název sloupce s datem v tabulce
        date_column_name = None
        for potential_date_column in ['date', 'week_start', 'next_month_start', 'time']:
            if potential_date_column in table_class.__dict__:
                date_column_name = potential_date_column
                break

        if not date_column_name:
            raise Exception(f"Tabulka {table_class.__name__} nemá sloupec s datem.")

        # Vytvoření filtrovacího intervalu pro celý den
        start_of_day = datetime.combine(date_object, datetime.min.time())
        end_of_day = datetime.combine(date_object, datetime.max.time())

        # Sestavení filtru na základě názvu sloupce s datem
        filter_condition = {
            date_column_name: (start_of_day, end_of_day)
        }

        # Přidání podmínky pro vybraný sloupec
        if column:
            filter_condition_column = {column: True}
            filter_condition.update(filter_condition_column)

        data = db.session.query(table_class).filter(
            *[
                getattr(table_class, k).between(v[0], v[1])
                if isinstance(v, tuple) and len(v) == 2
                else getattr(table_class, k) == v
                for k, v in filter_condition.items()
            ]
        ).all()

        data_list = [row.__dict__ for row in data]
        for item in data_list:
            item.pop('_sa_instance_state', None)
        return jsonify(data_list)
    except Exception as e:
        return jsonify({'error': str(e)})
    
#END POINTS   
@app.route('/api/data/last_data', methods=['GET'])
@jwt_required()
def get_last_weather_data():
    return get_last_data(BaseMeteostation)

@app.route('/api/data/aggregated/today', methods=['GET'])
@jwt_required()
def get_aggregated_data_today():
    column = request.args.get('column')
    return get_all_data_by_date_today(AggregatedData, column=column)
    
# Tato trasa bude sloužit k ověření uživatele
@app.route('/api/login', methods=['POST'])
def login():
    try:
        username = request.json['username']
        password = request.json['password']

        # Kontrola existence třídy Users
        if Users is None:
            return jsonify({'error': 'Table "users" not found in the database.'}), 500

        # Oprava použití db.session.query
        user = db.session.query(Users).filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            access_token = create_access_token_for_user(user)
            return jsonify(access_token=access_token), 200
        else:
            return jsonify({'error': 'Invalid username or password'}), 401

    except Exception as e:
        return jsonify({'error': str(e)}), 500

#Registrace uzivatele s kodem        
@app.route('/api/register', methods=['POST'])
def register():
    try:
        username = request.json['username']
        password = request.json['password']
        code = request.json['code']

        # Kontrola existence třídy Users
        if Users is None:
            return jsonify({'error': 'Table "users" not found in the database.'}), 500

        # Kontrola, zda uživatel s daným jménem již neexistuje
        existing_user = db.session.query(Users).filter_by(username=username).first()
        if existing_user:
            return jsonify({'error': 'Username already exists'}), 400

        # Kontrola existence zadaného kódu v tabulce meteo_codes
        meteo_code = get_meteo_code(code)
        if not meteo_code:
            return jsonify({'error': 'Invalid code'}), 400

        # Vytvoření nového uživatele
        access_token = create_access_token(identity=username)
        new_user = Users(username=username, password=generate_password_hash(password, method='sha256'), token=access_token)
        db.session.add(new_user)
        db.session.commit()

        # Vytvoření přístupového a obnovovacího tokenu pro nově zaregistrovaného uživatele
        return jsonify({'message': 'User successfully registered', 'access_token': access_token}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500        

@app.route('/api/is_valid', methods=['GET'])
def is_valid():
    return {'valid_token': 1}, 200
    
@app.route('/api/data/daily_test', methods=['GET'])
@jwt_required()
def get_daily_data_test():
    date = request.args.get('date')
    columns = request.args.get('columns')
    return get_data_by_columns_and_date_test(AggregatedDailyData, date=date, columns=columns)

@app.route('/api/data/weekly/cols', methods=['GET'])
@jwt_required()
def get_weekly_data_columns(columns=None):
    columns = request.args.get('columns')
    return get_data_by_columns(AggregatedWeeklyData, columns=columns)
    
@app.route('/api/data/daily/<date>', methods=['GET'])
@app.route('/api/data/daily', methods=['GET'])
@jwt_required()
def get_daily_data(date=None):
    column = request.args.get('column')
    if date:
        return get_data_by_date_and_column(AggregatedDailyData, date, time=request.args.get('week_start'), column=column)
    else:
        return get_all_data(AggregatedDailyData, column=column)

@app.route('/api/data/weekly/<date>', methods=['GET'])
@app.route('/api/data/weekly', methods=['GET'])
@jwt_required()
def get_weekly_data(date=None):
    column = request.args.get('column')
    if date:
        return get_data_by_date_and_column(AggregatedWeeklyData, date, time=request.args.get('week_start'), column=column)
    else:
        return get_all_data(AggregatedWeeklyData, column=column)

@app.route('/api/data/monthly/<date>', methods=['GET'])
@app.route('/api/data/monthly', methods=['GET'])
@jwt_required()
def get_monthly_data(date=None):
    column = request.args.get('column')
    if date: 
        return get_data_by_date_and_column(AggregatedMonthlyData, date, time=request.args.get('next_month_start'), column=column)
    else:
        return get_all_data(AggregatedMonthlyData, column=column)

@app.route('/api/data/aggregated/<date>', methods=['GET'])
@app.route('/api/data/aggregated', methods=['GET'])
@jwt_required()
def get_aggregated_data(date=None):
    column = request.args.get('column')
    if date: 
        return get_data_by_date_and_column(AggregatedData, date ,time=request.args.get('time'), column=column)
    else:
        return get_all_data(AggregatedData, column=column)
        
@app.route('/api/columns', methods=['GET'])
@jwt_required()
def get_columns():
    return get_all_columns(AggregatedData)
    
@app.route('/api/test/run_all_tests', methods=['GET'])
def run_all_tests():
    # Spuštění všech testů
    test_result = unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(TEST.TestFlaskAPI))
    
    # Získání výsledků testů
    num_tests_run = test_result.testsRun
    num_failures = len(test_result.failures)
    num_errors = len(test_result.errors)
    num_skipped = len(test_result.skipped)
    
    # Sestavení výsledků do JSON odpovědi
    response = {
        "num_tests_run": num_tests_run,
        "num_failures": num_failures,
        "num_errors": num_errors,
        "num_skipped": num_skipped,
        "tests_passed": num_failures == 0 and num_errors == 0
    }
    
    return jsonify(response)
    
@app.route('/api/data/meteostation/today', methods=['GET'])
@jwt_required()
def get_meteostation_data_today():
    try:
        # Získání aktuálního data
        today = datetime.now().date()

        # Získání dat z tabulky BaseMeteostation pro dnešní den
        data = db.session.query(BaseMeteostation).filter(BaseMeteostation.time >= today).all()

        # Příprava výstupu
        data_list = [row.__dict__ for row in data]
        for item in data_list:
            item.pop('_sa_instance_state', None)

        return jsonify(data_list)

    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/api/data/meteostation/<date>', methods=['GET'])
@jwt_required()
def get_meteostation_data_by_date(date):
    try:
        # Převedení řetězce s datem na objekt datetime
        selected_date = datetime.strptime(date, '%Y-%m-%d').date()

        # Získání dat z tabulky BaseMeteostation pro zadané datum
        data = db.session.query(BaseMeteostation).filter(func.date(BaseMeteostation.time) == selected_date).all()

        # Příprava výstupu
        data_list = [row.__dict__ for row in data]
        for item in data_list:
            item.pop('_sa_instance_state', None)

        return jsonify(data_list)

    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/data/meteostation/today/max', methods=['GET'])
@jwt_required()
def get_meteostation_max_today():
    try:
        # Získání aktuálního data
        today = datetime.now().date()

        # Získání dat z tabulky BaseMeteostation pro dnešní den
        data_today = db.session.query(BaseMeteostation).filter(BaseMeteostation.time >= today, BaseMeteostation.time < today + timedelta(days=1)).all()

        # Inicializace slovníku pro maximální hodnoty
        max_values_dict = {}

        # Projití všech sloupců tabulky
        for column in BaseMeteostation.__table__.columns:
            column_name = column.key
            max_value = None

            # Projití všech dat pro daný sloupec a nalezení maximální hodnoty
            for row in data_today:
                value = getattr(row, column_name)
                if max_value is None or value > max_value:
                    max_value = value

            # Přidání maximální hodnoty do slovníku
            max_values_dict[column_name] = max_value

        return jsonify(max_values_dict)

    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/api/data/meteostation/today/min', methods=['GET'])
@jwt_required()
def get_meteostation_min_today():
    try:
        # Získání aktuálního data
        today = datetime.now().date()

        # Získání dat z tabulky BaseMeteostation pro dnešní den
        data_today = db.session.query(BaseMeteostation).filter(BaseMeteostation.time >= today, BaseMeteostation.time < today + timedelta(days=1)).all()

        # Inicializace slovníku pro minimální hodnoty
        min_values_dict = {}

        # Projití všech sloupců tabulky
        for column in BaseMeteostation.__table__.columns:
            column_name = column.key
            min_value = None

            # Projití všech dat pro daný sloupec a nalezení minimální hodnoty
            for row in data_today:
                value = getattr(row, column_name)
                if min_value is None or value < min_value:
                    min_value = value

            # Přidání minimální hodnoty do slovníku
            min_values_dict[column_name] = min_value

        return jsonify(min_values_dict)

    except Exception as e:
        return jsonify({'error': str(e)})
        
@app.route('/api/data/meteostation/min/<date>', methods=['GET'])
@jwt_required()
def get_meteostation_min_by_date(date):
    try:
        # Převedení řetězce s datem na objekt datetime
        selected_date = datetime.strptime(date, '%Y-%m-%d').date()

        # Získání minimálních hodnot pro všechny sloupce z tabulky BaseMeteostation pro zadané datum
        min_values_query = db.session.query(*[func.min(getattr(BaseMeteostation, column.name)) for column in BaseMeteostation.__table__.columns]).filter(func.date(BaseMeteostation.time) == selected_date)
        min_values = min_values_query.first()

        # Příprava výstupu
        min_values_dict = {column.key: value for column, value in zip(BaseMeteostation.__table__.columns, min_values)}

        return jsonify(min_values_dict)

    except Exception as e:
        return jsonify({'error': str(e)})
        
@app.route('/api/data/meteostation/max/<date>', methods=['GET'])
@jwt_required()
def get_meteostation_max_by_date(date):
    try:
        # Převedení řetězce s datem na objekt datetime
        selected_date = datetime.strptime(date, '%Y-%m-%d').date()

        # Získání maximálních hodnot pro všechny sloupce z tabulky BaseMeteostation pro zadané datum
        max_values_query = db.session.query(*[func.max(getattr(BaseMeteostation, column.name)) for column in BaseMeteostation.__table__.columns]).filter(func.date(BaseMeteostation.time) == selected_date)
        max_values = max_values_query.first()

        # Příprava výstupu
        max_values_dict = {column.key: value for column, value in zip(BaseMeteostation.__table__.columns, max_values)}

        return jsonify(max_values_dict)

    except Exception as e:
        return jsonify({'error': str(e)})
        
@app.route('/api/data/weekly_test/<date>', methods=['GET'])
@jwt_required()
def get_weekly_data_by_date_test(date):
    try:
        # Převedení řetězce s datem na objekt datetime
        selected_date = datetime.strptime(date, '%Y-%m-%d').date()

        # Zjištění prvního dne týdne obsahující zadané datum
        first_day_of_week = selected_date - timedelta(days=selected_date.weekday())

        # Získání dat z tabulky AggregatedDailyData pro daný týden
        #weekly_data = db.session.query(AggregatedDailyData).filter(func.date_trunc('week', AggregatedDailyData.week_start) == first_day_of_week).all()
        weekly_data = db.session.query(AggregatedDailyData).filter(func.DATE(AggregatedDailyData.week_start) >= first_day_of_week, func.DATE(AggregatedDailyData.week_start) < first_day_of_week + timedelta(days=7)).all()

        # Příprava výstupu
        data_list = [row.__dict__ for row in weekly_data]
        for item in data_list:
            item.pop('_sa_instance_state', None)

        return jsonify(data_list)

    except Exception as e:
        return jsonify({'error': str(e)})
        
@app.route('/api/data/monthly_test/<date>', methods=['GET'])
@jwt_required()
def get_monthly_data_by_date(date):
    try:
        # Převedení řetězce s datem na objekt datetime
        selected_date = datetime.strptime(date, '%Y-%m-%d').date()

        # Získání roku a měsíce ze zadaného data
        year = selected_date.year
        month = selected_date.month

        # Získání dat z tabulky AggregatedDailyData pro daný měsíc
        monthly_data = db.session.query(AggregatedDailyData).filter(extract('year', AggregatedDailyData.week_start) == year, extract('month', AggregatedDailyData.week_start) == month).all()

        # Příprava výstupu
        data_list = [row.__dict__ for row in monthly_data]
        for item in data_list:
            item.pop('_sa_instance_state', None)

        return jsonify(data_list)

    except Exception as e:
        return jsonify({'error': str(e)})
        
@app.route('/api/data/hourly/weekly/<date>', methods=['GET'])
@jwt_required()
def get_hourly_data_weekly_by_date(date):
    try:
        # Převedení řetězce s datem na objekt datetime
        selected_date = datetime.strptime(date, '%Y-%m-%d').date()

        # Zjištění prvního dne týdne, ke kterému zadané datum patří
        first_day_of_week = selected_date - timedelta(days=selected_date.weekday())

        # Získání dat z tabulky BaseMeteostation pro každý den daného týdne
        hourly_data_weekly = []
        for i in range(7):
            # Získání dat pro každý den týdne
            selected_date = first_day_of_week + timedelta(days=i)
            hourly_data_daily = db.session.query(AggregatedData).filter(func.date(AggregatedData.time) == selected_date).all()
            hourly_data_weekly.extend(hourly_data_daily)

        # Příprava výstupu
        data_list = [row.__dict__ for row in hourly_data_weekly]
        for item in data_list:
            item.pop('_sa_instance_state', None)

        return jsonify(data_list)

    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/data/4hourly/monthly/<date>', methods=['GET'])
@jwt_required()
def get_4hourly_data_monthly_by_date(date):
    try:
        # Převedení řetězce s datem na objekt datetime
        selected_date = datetime.strptime(date, '%Y-%m-%d').date()

        # Získání roku a měsíce zadaného data
        year = selected_date.year
        month = selected_date.month

        # Získání dat z tabulky BaseMeteostation pro daný měsíc, kde čas odpovídá 0, 4, 8, 12, 16 a 20 hodin
        hourly_data_monthly = db.session.query(AggregatedData).filter(
            extract('year', AggregatedData.time) == year,
            extract('month', AggregatedData.time) == month,
            extract('hour', AggregatedData.time).in_([0, 4, 8, 12, 16, 20])
        ).all()

        # Příprava výstupu
        data_list = [row.__dict__ for row in hourly_data_monthly]
        for item in data_list:
            item.pop('_sa_instance_state', None)

        return jsonify(data_list)

    except Exception as e:
        return jsonify({'error': str(e)})
        
@app.route('/api/data/daily/yearly/<date>', methods=['GET'])
@jwt_required()
def get_daily_data_yearly_by_date(date):
    try:
        # Převedení řetězce s datem na objekt datetime
        selected_date = datetime.strptime(date, '%Y-%m-%d')

        # Získání roku z vybraného data
        selected_year = selected_date.year

        # Získání dat z tabulky AggregatedDailyData pro daný rok
        daily_data_yearly = db.session.query(AggregatedDailyData).filter(
            extract('year', AggregatedDailyData.week_start) == selected_year
        ).all()

        # Příprava výstupu
        data_list = [row.__dict__ for row in daily_data_yearly]
        for item in data_list:
            item.pop('_sa_instance_state', None)

        return jsonify(data_list)

    except Exception as e:
        return jsonify({'error': str(e)})
        
@app.route('/api/data/meteostation/all_last_data', methods=['GET'])
@jwt_required()
def get_all_last_meteostation_data():
    try:
        # Získání posledních dat z tabulky BaseMeteostation
        last_data = db.session.query(BaseMeteostation).order_by(desc(BaseMeteostation.time)).first()

        # Pokud nebyla žádná data nalezena, vrátíme chybovou zprávu
        if not last_data:
            return jsonify({'error': 'No data found in the database.'}), 404

        # Získání data z posledního záznamu
        reference_date = last_data.time.date()

        # Vytvoření časového rozmezí od 00:00:00 do 23:59:59 pro vybraný den
        start_of_day = datetime.combine(reference_date, datetime.min.time())
        end_of_day = datetime.combine(reference_date, datetime.max.time())

        # Získání posledních dat z tabulky pro vybraný den
        last_data_for_day = db.session.query(BaseMeteostation).filter(
            BaseMeteostation.time.between(start_of_day, end_of_day)
        ).all()

        # Příprava výstupu
        data_list = [row.__dict__ for row in last_data_for_day]
        for item in data_list:
            item.pop('_sa_instance_state', None)

        return jsonify(data_list)

    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
