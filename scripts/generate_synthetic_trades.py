import sys
import os
import uuid
import random
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.models import init_db, SessionLocal, PaperTrade

def generate_synthetic_trades():
    init_db()
    session = SessionLocal()
    
    # Check if there are already trades
    if session.query(PaperTrade).count() > 0:
        print("Database already has trades. Skipping synthetic generation.")
        session.close()
        return
        
    print("Generating synthetic trades...")
    start_time = datetime.now() - timedelta(days=30)
    
    strategies = [
        ('Iron Condor', 4, 30.0, -15.0), # TP, SL targets roughly
        ('Bull Put Spread', 2, 20.0, -10.0),
        ('Bear Call Spread', 2, 20.0, -10.0)
    ]
    
    for i in range(20):
        group_id = str(uuid.uuid4())
        strat_name, legs, tp, sl = random.choice(strategies)
        
        entry_time = start_time + timedelta(days=i, hours=random.randint(1, 5))
        exit_time = entry_time + timedelta(hours=random.randint(1, 4))
        
        # Simulate Win or Loss
        is_win = random.random() < 0.65 # 65% win rate roughly
        if is_win:
            net_pnl = random.uniform(5.0, tp)
            reason = 'TP' if net_pnl > (tp * 0.9) else 'EOD'
        else:
            net_pnl = random.uniform(sl, -2.0)
            reason = 'SL' if net_pnl < (sl * 0.9) else 'EOD'
            
        for leg in range(legs):
            t = PaperTrade(
                group_id=group_id,
                action='SELL' if leg % 2 == 0 else 'BUY',
                symbol=f'NIFTY_LEG_{leg}',
                token=f'1234{leg}',
                option_type='CE' if random.random() > 0.5 else 'PE',
                entry_time=entry_time,
                entry_price=100.0,
                exit_time=exit_time,
                exit_price=100.0, # not really used since we group by pnl
                pnl=net_pnl,
                status='CLOSED',
                exit_reason=reason
            )
            session.add(t)
            
    # Add one active position
    active_group = str(uuid.uuid4())
    active_entry = datetime.now()
    for leg in range(4): # Active Iron Condor
         t = PaperTrade(
             group_id=active_group,
             action='SELL' if leg % 2 == 0 else 'BUY',
             symbol=f'NIFTY_ACTIVE_{leg}',
             token=f'9999{leg}',
             option_type='CE' if leg < 2 else 'PE',
             entry_time=active_entry,
             entry_price=150.0,
             status='OPEN'
         )
         session.add(t)
         
    session.commit()
    session.close()
    print("Done!")

if __name__ == '__main__':
    generate_synthetic_trades()
