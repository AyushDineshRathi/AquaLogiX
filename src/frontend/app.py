import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# --- Page Configuration ---
st.set_page_config(page_title="AquaLogix", page_icon="🌊", layout="wide")

st.title("🌊 AquaLogix")
st.markdown("Your conversational ocean data analyst. Ask any question about the ARGO float data.")

# --- Initialize chat history in session state ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Display previous chat messages ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # A simple way to handle content that might be complex dicts/lists
        if isinstance(message["content"], str):
            st.markdown(message["content"])
        else:
            st.write(message["content"]) # Fallback for non-string content

if user_question := st.chat_input("Ask a question about the ARGO data..."):
    # Add user message to chat history and display it
    st.session_state.messages.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(user_question)

    # --- Logic to process the user's question ---
    with st.chat_message("assistant"):
        with st.spinner("AquaLogix is thinking..."):
            try:
                api_url = "http://127.0.0.1:8000/query"
                
                # Send the latest question and the relevant history
                payload = {
                    "question": user_question,
                    "history": st.session_state.messages[:-1] # Send all but the last message
                }
                response = requests.post(api_url, json=payload)
                
                if response.status_code == 200:
                    result_data = response.json()
                    
                    columns = result_data.get('columns', [])
                    rows = result_data.get('rows', [])
                    viz_type = result_data.get('visualization_type', 'table')
                    assistant_response_summary = "Here is the result for your query."

                    if not rows:
                        st.write("The query returned no results.")
                        assistant_response_summary = "The query returned no results."
                    else:
                        df = pd.DataFrame(rows, columns=columns)
                        
                        if viz_type == 'line_chart' and 'pressure' in df.columns and ('temperature' in df.columns or 'salinity' in df.columns):
                            y_axis = 'temperature' if 'temperature' in df.columns else 'salinity'
                            fig = px.line(df, x='pressure', y=y_axis, title=f"{y_axis.capitalize()} Profile")
                            fig.update_layout(xaxis_title="Pressure (Depth)", yaxis_title=y_axis.capitalize())
                            fig.update_xaxes(autorange="reversed")
                            st.plotly_chart(fig, use_container_width=True)
                            assistant_response_summary = f"Displayed a line chart for the {y_axis} profile."
                            with st.expander("Show Raw Data Table"): st.dataframe(df)

                        elif viz_type == 'bar_chart' and len(df.columns) == 2:
                            if pd.api.types.is_numeric_dtype(df.iloc[:, 0]):
                                val_col, cat_col = df.columns[0], df.columns[1]
                            else:
                                cat_col, val_col = df.columns[0], df.columns[1]
                            fig = px.bar(df, x=cat_col, y=val_col, title=f"{val_col.capitalize()} by {cat_col.capitalize()}")
                            fig.update_layout(xaxis_title=cat_col.capitalize(), yaxis_title=val_col.capitalize())
                            st.plotly_chart(fig, use_container_width=True)
                            assistant_response_summary = f"Displayed a bar chart of {val_col} by {cat_col}."
                            with st.expander("Show Raw Data Table"): st.dataframe(df)
                        
                        elif viz_type == 'map' and 'latitude' in df.columns and 'longitude' in df.columns:
                            map_df = df.copy()
                            map_df.rename(columns={"latitude": "lat", "longitude": "lon"}, inplace=True)
                            st.map(map_df)
                            assistant_response_summary = "Displayed the requested locations on a map."
                            with st.expander("Show Raw Data Table"): st.dataframe(df)

                        elif viz_type == 'metric' and len(df) == 1 and len(df.columns) == 1:
                            st.metric(label=df.columns[0], value=f"{df.iloc[0,0]:.2f}")
                            assistant_response_summary = f"The result is {df.iloc[0,0]:.2f}."

                        else: # Default to table
                            st.dataframe(df)
                            assistant_response_summary = "Here is the data in a table."

                    with st.expander("Show Generated SQL Query"):
                        st.code(result_data.get('query', ''), language='sql')
                        
                else: # Handle API errors
                    error_details = response.json().get('detail', 'Unknown error')
                    st.error(f"Error from API: {error_details}")
                    assistant_response_summary = f"Sorry, an error occurred: {error_details}"

            except Exception as e:
                st.error(f"An error occurred: {e}")
                assistant_response_summary = f"Sorry, an unexpected error occurred: {e}"
            
            # Add the assistant's summary to the chat history
            st.session_state.messages.append({"role": "assistant", "content": assistant_response_summary})