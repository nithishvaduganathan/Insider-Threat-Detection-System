import os
import numpy as np
import pandas as pd
import joblib
import random
import time
import threading
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.utils import secure_filename
from sklearn.feature_extraction.text import CountVectorizer
import re
from pyvis.network import Network
import networkx as nx
from flask import send_file



app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Hardcoded admin credentials
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'

# Suspicious keywords
SUSPICIOUS_KEYWORDS = ['confidential', 'urgent', 'password', 'secret', 'invoice', 'transfer']

# Global variables for models
classifier = None
regressor = None
scaler = None

# Load ML models
def load_models():
    global classifier, regressor, scaler
    try:
        classifier = joblib.load('models/best_classifier.pkl')
        regressor = joblib.load('models/best_regressor.pkl')
        scaler = joblib.load('models/scaler.pkl')
        print("Models loaded successfully!")
        return True
    except Exception as e:
        print(f"Error loading models: {e}")
        return False

# Try to load models at startup
models_loaded = load_models()

# Global variable to store live logs
live_logs = []

# Store all logs generated today (for CSV export)
daily_log_buffer = []
current_log_date = datetime.now().date()


# User profiles for generating realistic logs
user_profiles = {}
for i in range(1, 31):
    user_id = f"user{i}"
    user_profiles[user_id] = {
        'email': f"{user_id}@gmail.com",
        'login_mean': np.random.normal(8.5, 0.5),
        'login_std': 0.3,
        'file_mean': np.random.normal(35, 10),
        'file_std': 8,
        'email_mean': np.random.normal(25, 5),
        'email_std': 4,
        'usb_prob': np.random.uniform(0.1, 0.3),
        'out_of_session_prob': np.random.uniform(0.05, 0.15),
        'keyword_prob': np.random.uniform(0.02, 0.08)
    }

def get_today_log_path():
    today_str = datetime.now().strftime("%Y-%m-%d")
    log_dir = "uploads"
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, f"log-{today_str}.csv")


# Function to generate synthetic logs
def generate_synthetic_logs():
    global live_logs, daily_log_buffer, current_log_date

    logs = []
    now = datetime.now()

    # Reset daily buffer if date changes
    if now.date() != current_log_date:
        daily_log_buffer = []
        current_log_date = now.date()

    for user_id, profile in user_profiles.items():

        # Decide red team behavior
        is_red_team = 1 if random.random() < 0.3 else 0

        if is_red_team:
            #  Red Team (Insider-like)
            login_duration = round(random.uniform(9.5, 12.0), 1)
            file_access = random.randint(70, 120)
            usb_plug = random.randint(2, 5)
            usb_duration = random.randint(90, 200)
            email_total = random.randint(40, 70)
            email_suspicious = random.randint(3, 8)
            out_of_session = random.randint(1, 4)
            anomaly_score = round(random.uniform(0.75, 0.98), 2)

            # High probability of sensitive keywords
            has_confidential = 1 if random.random() < 0.8 else 0
            has_urgent = 1 if random.random() < 0.7 else 0
            has_password = 1 if random.random() < 0.75 else 0
            has_secret = 1 if random.random() < 0.7 else 0
            has_invoice = 1 if random.random() < 0.6 else 0
            has_transfer = 1 if random.random() < 0.65 else 0

        else:
            #  Normal User
            login_duration = round(
                max(6.0, min(11.0, np.random.normal(profile['login_mean'], 0.3))), 1
            )
            file_access = max(10, int(np.random.normal(profile['file_mean'], 8)))
            usb_plug = 1 if random.random() < profile['usb_prob'] else 0
            usb_duration = random.randint(10, 50) if usb_plug else 0
            email_total = max(10, int(np.random.normal(profile['email_mean'], 4)))
            email_suspicious = random.randint(0, 2)
            out_of_session = 1 if random.random() < profile['out_of_session_prob'] else 0
            anomaly_score = round(random.uniform(0.05, 0.35), 2)

            # Low probability of sensitive keywords
            has_confidential = 1 if random.random() < profile['keyword_prob'] * 2 else 0
            has_urgent = 1 if random.random() < profile['keyword_prob'] * 1.5 else 0
            has_password = 1 if random.random() < profile['keyword_prob'] * 0.6 else 0
            has_secret = 1 if random.random() < profile['keyword_prob'] * 0.4 else 0
            has_invoice = 1 if random.random() < profile['keyword_prob'] * 3 else 0
            has_transfer = 1 if random.random() < profile['keyword_prob'] * 1.2 else 0

        # Calculate suspicious email ratio
        email_suspicious_ratio = round(
            email_suspicious / email_total, 3
        ) if email_total > 0 else 0.0

        
        log = {
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": user_id,
            "email": profile["email"],
            "login_duration_hours": login_duration,
            "file_access_count": file_access,
            "usb_plug_count": usb_plug,
            "usb_total_duration_min": usb_duration,
            "email_total_count": email_total,
            "email_suspicious_count": email_suspicious,
            "email_suspicious_ratio": email_suspicious_ratio,
            "out_of_session_count": out_of_session,
            "has_confidential": has_confidential,
            "has_urgent": has_urgent,
            "has_password": has_password,
            "has_secret": has_secret,
            "has_invoice": has_invoice,
            "has_transfer": has_transfer,
            "anomaly_score": anomaly_score,
            "is_red_team": is_red_team
        }

        logs.append(log)
        

    live_logs = logs

    

    return logs

def save_log_archive(logs):
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"log-{ts}.csv"
    path = os.path.join("uploads", filename)
    pd.DataFrame(logs).to_csv(path, index=False)

def save_log_archive(logs):
    if not logs:
        return

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"log-{ts}.csv"
    path = os.path.join("uploads", filename)
    pd.DataFrame(logs).to_csv(path, index=False)


# Background thread to update logs every minute
def update_logs_periodically():
    while True:
        logs = generate_synthetic_logs()

        # Save snapshot to archive (All Logs)
        save_log_archive(logs)

        time.sleep(60)


# Start the background thread
thread = threading.Thread(target=update_logs_periodically, daemon=True)
thread.start()

# Function to generate PyVis graph
def generate_pyvis_graph():
    global live_logs
    
    # Create a NetworkX graph
    G = nx.Graph()
    
    # Add nodes and edges based on live logs
    for log in live_logs:
        user_id = log['user_id']
        
        # Add user node
        G.add_node(user_id, type='user', anomaly_score=log['anomaly_score'], 
                  is_red_team=log['is_red_team'], email=log['email'])
        
        # Add file access edges
        if log['file_access_count'] > 50:
            file_node = f"file_{user_id}"
            G.add_node(file_node, type='file', count=log['file_access_count'])
            G.add_edge(user_id, file_node, type='file_access', weight=log['file_access_count'])
        
        # Add USB usage edges
        if log['usb_plug_count'] > 0:
            usb_node = f"usb_{user_id}"
            G.add_node(usb_node, type='usb', count=log['usb_plug_count'], duration=log['usb_total_duration_min'])
            G.add_edge(user_id, usb_node, type='usb_usage', weight=log['usb_plug_count'])
        
        # Add email edges
        if log['email_suspicious_count'] > 0:
            email_node = f"email_{user_id}"
            G.add_node(email_node, type='email', count=log['email_suspicious_count'])
            G.add_edge(user_id, email_node, type='email_suspicious', weight=log['email_suspicious_count'])
    
    # Create PyVis network
    net = Network(height='600px', width='100%', bgcolor='#222222', font_color='white')
    
    # Configure physics for better visualization
    net.set_options('''
    {
      "physics": {
        "enabled": true,
        "stabilization": {"enabled": true, "fit": true, "iterations": 2000},
        "barnesHut": {
          "gravitationalConstant": -2000,
          "centralGravity": 0.1,
          "springLength": 200,
          "springConstant": 0.01,
          "damping": 0.85,
          "avoidOverlap": 1
        }
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 200
      },
      "nodes": {
        "font": {
          "size": 12
        }
      }
    }
    ''')
    
    # Add nodes to PyVis network
    for node, attrs in G.nodes(data=True):
        node_type = attrs.get('type', 'unknown')
        
        if node_type == 'user':
            anomaly_score = attrs.get('anomaly_score', 0)
            is_red_team = attrs.get('is_red_team', 0)
            email = attrs.get('email', '')
            
            # Find the corresponding log entry for this user
            user_log = next((log for log in live_logs if log['user_id'] == node), None)
            
            # Determine color and size based on risk level
            if is_red_team:
                color = 'red'
                size = 30
                
                # Create detailed explanation for red team users
                reasons = []
                
                if user_log:
                    # Check USB usage
                    if user_log['usb_plug_count'] > 2:
                        reasons.append(f"High USB usage ({user_log['usb_plug_count']} plugs)")
                    if user_log['usb_total_duration_min'] > 100:
                        reasons.append(f"Long USB duration ({user_log['usb_total_duration_min']} minutes)")
                    
                    # Check file access
                    if user_log['file_access_count'] > 60:
                        reasons.append(f"Excessive file access ({user_log['file_access_count']} files)")
                    
                    # Check email activity
                    if user_log['email_suspicious_count'] > 3:
                        reasons.append(f"Multiple suspicious emails ({user_log['email_suspicious_count']})")
                    if user_log['email_suspicious_ratio'] > 0.2:
                        reasons.append(f"High suspicious email ratio ({user_log['email_suspicious_ratio']*100:.1f}%)")
                    
                    # Check login duration
                    if user_log['login_duration_hours'] < 6:
                        reasons.append(f"Unusually short login duration ({user_log['login_duration_hours']} hours)")
                    elif user_log['login_duration_hours'] > 11:
                        reasons.append(f"Unusually long login duration ({user_log['login_duration_hours']} hours)")
                    
                    # Check out of session access
                    if user_log['out_of_session_count'] > 1:
                        reasons.append(f"Multiple out-of-session accesses ({user_log['out_of_session_count']})")
                    
                    # Check for suspicious keywords
                    keyword_flags = []
                    if user_log['has_confidential']:
                        keyword_flags.append("confidential")
                    if user_log['has_urgent']:
                        keyword_flags.append("urgent")
                    if user_log['has_password']:
                        keyword_flags.append("password")
                    if user_log['has_secret']:
                        keyword_flags.append("secret")
                    if user_log['has_invoice']:
                        keyword_flags.append("invoice")
                    if user_log['has_transfer']:
                        keyword_flags.append("transfer")
                    
                    if keyword_flags:
                        reasons.append(f"Emails contain suspicious keywords: {', '.join(keyword_flags)}")
                
                # Create the tooltip with detailed reasons
                if reasons:
                    # Format without HTML tags
                    title = f"User: {node}\nEmail: {email}\n\nFLAGGED AS RED TEAM BECAUSE:\n" + "\n".join(f"• {reason}" for reason in reasons)
                else:
                    title = f"User: {node}\nEmail: {email}\nAnomaly Score: {anomaly_score:.2f}\nRed Team: Yes"
                
            elif anomaly_score > 0.7:
                color = 'orange'
                size = 25
                
                # Create explanation for high anomaly score users
                reasons = []
                
                if user_log:
                    # Check for any concerning behavior
                    if user_log['usb_plug_count'] > 0:
                        reasons.append(f"USB usage detected ({user_log['usb_plug_count']} plugs)")
                    if user_log['file_access_count'] > 40:
                        reasons.append(f"High file access ({user_log['file_access_count']} files)")
                    if user_log['email_suspicious_count'] > 0:
                        reasons.append(f"Suspicious emails detected ({user_log['email_suspicious_count']})")
                    if user_log['out_of_session_count'] > 0:
                        reasons.append(f"Out-of-session access ({user_log['out_of_session_count']})")
                
                # Create the tooltip with reasons
                if reasons:
                    title = f"User: {node}\nEmail: {email}\n\nHIGH RISK BECAUSE:\n" + "\n".join(f"• {reason}" for reason in reasons)
                else:
                    title = f"User: {node}\nEmail: {email}\nAnomaly Score: {anomaly_score:.2f}"
                
            elif anomaly_score > 0.4:
                color = 'yellow'
                size = 20
                title = f"User: {node}\nEmail: {email}\nAnomaly Score: {anomaly_score:.2f}\nRisk Level: Medium"
            else:
                color = 'lightblue'
                size = 15
                title = f"User: {node}\nEmail: {email}\nAnomaly Score: {anomaly_score:.2f}\nRisk Level: Low"
                
        elif node_type == 'file':
            color = 'green'
            size = 15
            title = f"File Access: {attrs.get('count', 0)} files"
            
        elif node_type == 'usb':
            color = 'purple'
            size = 15
            title = f"USB Usage: {attrs.get('count', 0)} plugs, {attrs.get('duration', 0)} min"
            
        elif node_type == 'email':
            color = '#ff9900'
            size = 15
            title = f"Suspicious Emails: {attrs.get('count', 0)}"
            
        else:
            color = 'gray'
            size = 10
            title = str(node)
        
        net.add_node(node, label=str(node), color=color, size=size, title=title)
    
    # Add edges to PyVis network
    for u, v, attrs in G.edges(data=True):
        edge_type = attrs.get('type', 'unknown')
        weight = attrs.get('weight', 1)
        
        if edge_type == 'file_access':
            color = 'green'
            width = 2 + weight/20
        elif edge_type == 'usb_usage':
            color = 'purple'
            width = 2 + weight/5
        elif edge_type == 'email_suspicious':
            color = '#ff9900'
            width = 2 + weight/3
        else:
            color = 'gray'
            width = 1
            
        net.add_edge(u, v, color=color, width=width, title=f"{edge_type}: {weight}")
    
    # Save graph to HTML file
    if not os.path.exists('static/graphs'):
        os.makedirs('static/graphs')
    
    # Generate a unique filename with timestamp to avoid caching issues
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    graph_path = f'static/graphs/network_{timestamp}.html'
    net.save_graph(graph_path)
    
    return graph_path.replace("static/", "")


# Routes
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['username'] = username
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/home')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('home.html')

@app.route('/manual_prediction', methods=['GET', 'POST'])
def manual_prediction():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Check if models are loaded
    global classifier, regressor, scaler
    if classifier is None or regressor is None or scaler is None:
        if not load_models():
            flash('Machine learning models could not be loaded. Please check the models directory.', 'danger')
            return render_template('manual_prediction.html')
    
    if request.method == 'POST':
        try:
            # Get form data
            login_duration = float(request.form['login_duration'])
            file_access = int(request.form['file_access'])
            usb_plug = int(request.form['usb_plug'])
            usb_duration = int(request.form['usb_duration'])
            email_total = int(request.form['email_total'])
            email_suspicious = int(request.form['email_suspicious'])
            out_of_session = int(request.form['out_of_session'])
            
            # Get email content
            email_content = request.form.get('email_content', '')
            
            # Check if file was uploaded
            if 'email_file' in request.files and request.files['email_file'].filename != '':
                file = request.files['email_file']
                if file:
                    email_content = file.read().decode('utf-8')
            
            # Analyze email content for suspicious keywords
            keyword_flags = {}
            for keyword in SUSPICIOUS_KEYWORDS:
                keyword_flags[keyword] = 1 if keyword.lower() in email_content.lower() else 0
            
            # Prepare feature vector
            features = np.array([
                login_duration,
                file_access,
                usb_plug,
                usb_duration,
                email_total,
                email_suspicious,
                email_suspicious / email_total if email_total > 0 else 0,
                out_of_session,
                keyword_flags['confidential'],
                keyword_flags['urgent'],
                keyword_flags['password'],
                keyword_flags['secret'],
                keyword_flags['invoice'],
                keyword_flags['transfer']
            ]).reshape(1, -1)
            
            # Scale features
            features_scaled = scaler.transform(features)
            
            # Make predictions
            red_team_pred = classifier.predict(features_scaled)[0]
            anomaly_score_pred = regressor.predict(features_scaled)[0]
            
            # Get probability
            red_team_prob = classifier.predict_proba(features_scaled)[0][1]
            
            # Prepare results
            results = {
                'is_red_team': int(red_team_pred),
                'red_team_probability': float(red_team_prob),
                'anomaly_score': float(anomaly_score_pred),
                'keyword_flags': keyword_flags,
                'email_content': email_content,
                'email_suspicious': any(keyword_flags.values())
            }
            
            return render_template('manual_prediction.html', results=results)
        
        except Exception as e:
            flash(f'Error during prediction: {str(e)}', 'danger')
            return render_template('manual_prediction.html')
    
    return render_template('manual_prediction.html')

@app.route('/live_log_prediction')
def live_log_prediction():
    if 'username' not in session:
        return redirect(url_for('login'))

    #  Do NOT generate graph until logs exist
    if not live_logs:
        graph_path = None
    else:
        try:
            graph_path = generate_pyvis_graph()
        except Exception as e:
            flash(f'Error generating graph: {str(e)}', 'danger')
            graph_path = None

    return render_template(
        'live_log_prediction.html',
        graph_path=graph_path
    )

@app.route('/all_logs')
def all_logs():
    if 'username' not in session:
        return redirect(url_for('login'))

    log_files = []

    if os.path.exists("uploads"):
        for f in os.listdir("uploads"):
            if f.startswith("log-") and f.endswith(".csv"):
                path = os.path.join("uploads", f)
                created = datetime.fromtimestamp(os.path.getmtime(path))
                log_files.append({
                    "filename": f,
                    "created": created.strftime("%Y-%m-%d %H:%M")
                })

    # Sort latest first
    log_files.sort(key=lambda x: x["created"], reverse=True)

    return render_template("all_logs.html", log_files=log_files)

@app.route('/download_log/<filename>')
def download_log(filename):
    if 'username' not in session:
        return redirect(url_for('login'))

    path = os.path.join("uploads", filename)

    if not os.path.exists(path):
        flash("Log file not found", "danger")
        return redirect(url_for('all_logs'))

    return send_file(path, as_attachment=True)



@app.route('/download_logs')
def download_logs():
    if 'username' not in session:
        return redirect(url_for('login'))

    if not live_logs:
        flash("No live logs available yet.", "warning")
        return redirect(url_for('live_log_prediction'))

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"live-log-{timestamp}.csv"
    path = os.path.join("uploads", filename)

    df = pd.DataFrame(live_logs)
    df.to_csv(path, index=False)

    return send_file(
        path,
        as_attachment=True,
        download_name=filename
    )



@app.route('/api/live_logs')
def api_live_logs():
    global live_logs
    return jsonify(live_logs)

@app.route('/api/graph_data')
def api_graph_data():
    global live_logs
    
    # Get flagged users
    flagged_users = [log for log in live_logs if log['is_red_team'] == 1]
    
    # Prepare graph data
    nodes = []
    links = []
    
    node_id = 0
    for user in flagged_users:
        # Add user node
        nodes.append({
            'id': node_id,
            'name': user['user_id'],
            'type': 'user',
            'email': user['email'],
            'anomaly_score': user['anomaly_score']
        })
        user_node_id = node_id
        node_id += 1
        
        # Add activity nodes if they have high values
        if user['usb_plug_count'] > 0:
            nodes.append({
                'id': node_id,
                'name': f"USB: {user['usb_plug_count']} plugs",
                'type': 'usb',
                'value': user['usb_plug_count']
            })
            links.append({
                'source': user_node_id,
                'target': node_id,
                'value': user['usb_plug_count']
            })
            node_id += 1
        
        if user['file_access_count'] > 50:
            nodes.append({
                'id': node_id,
                'name': f"Files: {user['file_access_count']} accesses",
                'type': 'file',
                'value': user['file_access_count']
            })
            links.append({
                'source': user_node_id,
                'target': node_id,
                'value': user['file_access_count']
            })
            node_id += 1
        
        if user['email_suspicious_count'] > 0:
            nodes.append({
                'id': node_id,
                'name': f"Emails: {user['email_suspicious_count']} suspicious",
                'type': 'email',
                'value': user['email_suspicious_count']
            })
            links.append({
                'source': user_node_id,
                'target': node_id,
                'value': user['email_suspicious_count']
            })
            node_id += 1
    
    return jsonify({
        'nodes': nodes,
        'links': links
    })

# New route to regenerate PyVis graph
@app.route('/api/regenerate_graph')
def api_regenerate_graph():
    try:
        graph_path = generate_pyvis_graph()
        return jsonify({'success': True, 'graph_path': graph_path})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    # Create directories if they don't exist
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    os.makedirs('static/images', exist_ok=True)
    os.makedirs('static/graphs', exist_ok=True)
    
    # Generate initial logs
    generate_synthetic_logs()
    
    app.run(debug=True)