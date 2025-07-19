import os
from agent.utils import get_client

def check_portfolio():
    client = get_client()
    portfolio_id = os.getenv('CB_PORTFOLIO_ID', '41624202-2edd-4c2a-8194-d680c5c4fd69')
    
    print('🔍 Checking current portfolio state...')
    try:
        # Get accounts directly
        accounts = client.get_accounts()
        print(f'Number of accounts: {len(accounts.accounts)}')
        
        # Check if there are any positions
        total_positions = 0
        total_value = 0
        for account in accounts.accounts:
            # Check if this account has any balance
            if hasattr(account, 'available_balance') and account.available_balance:
                if isinstance(account.available_balance, dict):
                    balance_value = account.available_balance.get('value', '0')
                else:
                    balance_value = str(account.available_balance)
                
                if balance_value != '0':
                    print(f'Account {account.currency}: ${balance_value}')
                    total_positions += 1
                    try:
                        total_value += float(balance_value)
                    except:
                        pass
        
        print(f'Total accounts with positions: {total_positions}')
        print(f'Total portfolio value: ${total_value:,.2f}')
        
        if total_positions == 0:
            print('⚠️ No existing positions found - this is expected for a new portfolio')
        else:
            print('✅ Found existing positions')
            
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_portfolio() 