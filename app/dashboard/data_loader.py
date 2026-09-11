import pandas as pd
from sqlalchemy.orm import Session
from loguru import logger

def load_trade_history(session: Session) -> pd.DataFrame:
    """
    Loads all CLOSED paper trades, groups them by group_id, and calculates the net outcome.
    """
    from app.database.models import PaperTrade
    
    # Query all closed trades
    trades = session.query(PaperTrade).filter_by(status='CLOSED').all()
    
    if not trades:
        return pd.DataFrame()
        
    data = []
    for t in trades:
        data.append({
            'group_id': t.group_id,
            'symbol': t.symbol,
            'option_type': t.option_type,
            'action': t.action,
            'entry_time': t.entry_time,
            'exit_time': t.exit_time,
            'entry_price': t.entry_price,
            'exit_price': t.exit_price,
            'pnl_pct': t.pnl,
            'exit_reason': t.exit_reason
        })
        
    df = pd.DataFrame(data)
    
    # Group by group_id
    grouped = []
    for gid, group in df.groupby('group_id'):
        # Determine strategy type based on legs
        legs = len(group)
        if legs == 4:
            strategy = "Iron Condor"
        elif legs == 2:
            if all(group['option_type'] == 'CE'):
                strategy = "Bear Call Spread"
            elif all(group['option_type'] == 'PE'):
                strategy = "Bull Put Spread"
            else:
                strategy = "Custom 2-Leg"
        elif legs == 1:
            action = group.iloc[0]['action']
            opt_type = group.iloc[0]['option_type']
            strategy = f"Naked {action} {opt_type}"
        else:
            strategy = f"Custom {legs}-Leg"
            
        entry_time = group['entry_time'].min()
        exit_time = group['exit_time'].max()
        exit_reason = group.iloc[0]['exit_reason'] # Assume same for group
        
        # Calculate cash PnL (Assume lot size 50 for NIFTY)
        cash_pnl = 0.0
        for _, row in group.iterrows():
            if row['action'] == 'BUY':
                gross = (row['exit_price'] - row['entry_price']) * 50
            else:
                gross = (row['entry_price'] - row['exit_price']) * 50
            # Rough estimate of transaction costs to make it realistic on dashboard
            costs = 120 if strategy == "Iron Condor" else 60 if "Spread" in strategy else 30
            cash_pnl += (gross - costs/legs) # distribute cost per leg
            
        net_pnl_pct = group['pnl_pct'].mean()
        
        grouped.append({
            'Strategy': strategy,
            'Entry Time': entry_time,
            'Exit Time': exit_time,
            'Net PnL %': round(net_pnl_pct, 2),
            'Cash PnL (₹)': round(cash_pnl, 2),
            'Exit Reason': exit_reason,
            'Legs': legs
        })
        
    grouped_df = pd.DataFrame(grouped).sort_values('Entry Time', ascending=False).reset_index(drop=True)
    return grouped_df

def load_active_positions(session: Session) -> pd.DataFrame:
    """
    Loads all OPEN paper trades.
    """
    from app.database.models import PaperTrade
    trades = session.query(PaperTrade).filter_by(status='OPEN').all()
    
    if not trades:
        return pd.DataFrame()
        
    data = []
    for t in trades:
        data.append({
            'Group': t.group_id[-6:], # Just show last 6 chars for brevity
            'Action': t.action,
            'Symbol': t.symbol,
            'Entry Time': t.entry_time,
            'Entry Price': t.entry_price
        })
        
    return pd.DataFrame(data)
