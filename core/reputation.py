# core/reputation.py
import json
import os
import time

class ReputationSystem:
    """Système de réputation (Trust Score 0-100)"""
    
    def __init__(self, data_dir):
        self.reputation_file = os.path.join(data_dir, "reputation.json")
        self.reputation = self.load()
    
    def load(self):
        if os.path.exists(self.reputation_file):
            with open(self.reputation_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save(self):
        with open(self.reputation_file, 'w') as f:
            json.dump(self.reputation, f, indent=2)
    
    def get(self, wallet_name):
        data = self.reputation.get(wallet_name, {
            'score': 100,
            'completed_trades': 0,
            'failed_trades': 0,
            'reports': 0
        })
        return data
    
    def add_success(self, wallet_name):
        data = self.get(wallet_name)
        data['completed_trades'] += 1
        data['score'] = min(100, data['score'] + 2)
        self.reputation[wallet_name] = data
        self.save()
    
    def add_failure(self, wallet_name):
        data = self.get(wallet_name)
        data['failed_trades'] += 1
        data['score'] = max(0, data['score'] - 25)
        self.reputation[wallet_name] = data
        self.save()
    
    def add_report(self, wallet_name, reason):
        data = self.get(wallet_name)
        data['reports'] += 1
        data['score'] = max(0, data['score'] - 15)
        self.reputation[wallet_name] = data
        self.save()
    
    def can_trade(self, wallet_name):
        data = self.get(wallet_name)
        if data['score'] < 30:
            return False, f"Score trop bas ({data['score']}/100)"
        if data['failed_trades'] >= 3:
            return False, f"Trop d'échecs ({data['failed_trades']}/3)"
        if data['reports'] >= 5:
            return False, f"Trop de signalements ({data['reports']}/5)"
        return True, "OK"
    
    def get_status(self, wallet_name):
        data = self.get(wallet_name)
        if data['score'] >= 70:
            status = "🟢 Excellent"
        elif data['score'] >= 50:
            status = "🟡 Bon"
        elif data['score'] >= 30:
            status = "🟠 Surveillé"
        else:
            status = "🔴 Suspendu"
        return {
            'score': data['score'],
            'status': status,
            'completed_trades': data['completed_trades'],
            'failed_trades': data['failed_trades'],
            'reports': data['reports']
        }