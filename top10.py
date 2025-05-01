def display_top10_charts(df):
    import streamlit as st
    import plotly.express as px

    st.subheader("📊 Top 10 Companies by Total Dollar Value")
    top_companies = df.groupby("Company")["Amount ($)"].sum().nlargest(10).reset_index()
    bar_chart = px.bar(
        top_companies,
        x="Company",
        y="Amount ($)",
        title="Top 10 Companies by Amount",
        labels={"Amount ($)": "Total Value ($)", "Company": "Company"},
        text_auto=True
    )
    st.plotly_chart(bar_chart, use_container_width=True)

    selected = st.selectbox("🔍 Click to see transactions for a company:", top_companies["Company"])
    if selected:
        sub_df = df[df["Company"] == selected].copy()
        sub_df.index = range(1, len(sub_df) + 1)
        sub_df["Amount ($)"] = sub_df["Amount ($)"].apply(lambda x: f"${x:,.0f}")
        sub_df["Price ($)"] = sub_df["Price ($)"].apply(lambda x: f"${x:,.2f}")
        st.dataframe(sub_df)
