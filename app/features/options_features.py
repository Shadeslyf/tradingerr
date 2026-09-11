import pandas as pd

class OptionsFeatures:
    @staticmethod
    def calculate_pcr(options_df: pd.DataFrame, spot_df: pd.DataFrame) -> pd.DataFrame:
        """
        options_df should have ['timestamp', 'option_type', 'open_interest', 'volume']
        We will group by timestamp and option_type, sum the OI and Volume, then calculate PCR.
        """
        if options_df.empty:
            return spot_df

        # Group options by timestamp and type
        agg_opts = options_df.groupby(['timestamp', 'option_type']).agg({
            'open_interest': 'sum',
            'volume': 'sum'
        }).reset_index()

        # Pivot to get CE and PE side by side
        pivoted = agg_opts.pivot(index='timestamp', columns='option_type', values=['open_interest', 'volume'])
        
        # Flatten columns
        pivoted.columns = [f'{col[1]}_{col[0]}' for col in pivoted.columns]
        
        # Handle cases where CE or PE might be missing entirely
        for col in ['CE_open_interest', 'PE_open_interest', 'CE_volume', 'PE_volume']:
            if col not in pivoted.columns:
                pivoted[col] = 0

        # Calculate ratios
        pivoted['PCR_OI'] = pivoted['PE_open_interest'] / pivoted['CE_open_interest'].replace(0, 1)
        pivoted['PCR_VOL'] = pivoted['PE_volume'] / pivoted['CE_volume'].replace(0, 1)
        
        pivoted['Total_Call_OI'] = pivoted['CE_open_interest']
        pivoted['Total_Put_OI'] = pivoted['PE_open_interest']

        # Merge with spot
        spot_df = spot_df.join(pivoted, how='left')
        
        # Forward fill options data because options might not tick every minute
        spot_df.ffill(inplace=True)
        
        # Calculate changes in OI
        spot_df['Change_Call_OI'] = spot_df['Total_Call_OI'].diff().fillna(0)
        spot_df['Change_Put_OI'] = spot_df['Total_Put_OI'].diff().fillna(0)

        return spot_df
