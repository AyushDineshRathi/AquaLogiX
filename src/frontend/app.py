import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="AquaLogix", page_icon="🌊", layout="wide")

st.title("🌊 AquaLogix")
st.markdown("Your conversational ocean data analyst. Ask any question about the ARGO float data.")

with st.form(key='query_form'):
    user_question = st.text_input("Enter your question:", placeholder="e.g., Show me the 5 most recent temperature and salinity readings")
    submit_button = st.form_submit_button(label='Ask AquaLogix')

if submit_button and user_question:
    api_url = "http://127.0.0.1:8000/query"
    
    with st.spinner("AquaLogix is thinking..."):
        try:
            payload = {"question": user_question}
            response = requests.post(api_url, json=payload)
            
            if response.status_code == 200:
                result_data = response.json()
                
                st.success("Query successful!")
                
                # --- MODIFICATION: Create and display a Pandas DataFrame ---
                columns = result_data.get('columns', [])
                rows = result_data.get('rows', [])
                
                if rows:
                    df = pd.DataFrame(rows, columns=columns)
                    st.dataframe(df) # Display the interactive table
                else:
                    st.write("The query returned no results.")

                # Optionally, show the generated SQL query in an expander
                with st.expander("Show Generated SQL Query"):
                    st.code(result_data.get('query', 'Could not generate query.'), language='sql')

            else:
                error_details = response.json().get('detail', 'Unknown error')
                st.error(f"Error from API: {error_details}")

        except requests.exceptions.ConnectionError:
            st.error("Connection Error: Could not connect to the backend API. Is the server running?")
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")