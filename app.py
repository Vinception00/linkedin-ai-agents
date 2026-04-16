import streamlit as st
import plotly.express as px
import pandas as pd
from dotenv import load_dotenv
from data.posts_db import PostsDB
from agent_poster.generator import PostGenerator
from agent_poster.publisher import LinkedInPublisher
from agent_poster.content_planner import ContentPlanner

load_dotenv()

st.set_page_config(
    page_title="LinkedIn AI Agent",
    page_icon="🤖",
    layout="wide"
)

db = PostsDB()

# ─── SIDEBAR ───
st.sidebar.title("LinkedIn AI Agent")
page = st.sidebar.radio("Navigation", [
    "Dashboard",
    "Générer un post",
    "Historique des posts"
])

# ─── PAGE DASHBOARD ───
if page == "Dashboard":
    st.title("Dashboard analytics")

    posts = db.get_all_posts()

    if not posts:
        st.info("Aucun post en base. Publie ton premier post dans 'Générer un post'.")
    else:
        df = pd.DataFrame(posts)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Posts publiés", len(df))
        col2.metric("Total likes", int(df["likes"].sum()))
        col3.metric("Total commentaires", int(df["commentaires"].sum()))
        col4.metric("Total vues", int(df["vues"].sum()))

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Engagement par type de post")
            df_type = df.groupby("type")[["likes", "commentaires", "vues"]].mean().reset_index()
            fig = px.bar(df_type, x="type", y=["likes", "commentaires"],
                        barmode="group", title="Moyenne likes & commentaires par type")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Vues par post")
            fig2 = px.bar(df.sort_values("date"), x="sujet", y="vues",
                         title="Vues par post", color="type")
            fig2.update_xaxes(tickangle=45)
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Évolution de l'engagement dans le temps")
        df["date"] = pd.to_datetime(df["date"])
        fig3 = px.line(df.sort_values("date"), x="date", y="likes",
                      markers=True, title="Likes dans le temps", color="type")
        st.plotly_chart(fig3, use_container_width=True)

        st.subheader("Détail des posts")
        st.dataframe(
            df[["date", "type", "sujet", "likes", "commentaires", "republications", "vues"]],
            use_container_width=True,
            hide_index=True
        )

# ─── PAGE GÉNÉRER UN POST ───
elif page == "Générer un post":
    st.title("Générer un post LinkedIn")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Paramètres")
        post_type = st.selectbox("Type de post", ["conseil", "story", "veille"])
        use_planner = st.checkbox("Laisser Claude choisir le sujet", value=True)

        if use_planner:
            sujet = None
        else:
            sujet = st.text_input("Sujet personnalisé")

        contexte = st.text_area("Contexte / détails personnels", height=100)
        dry_run = st.checkbox("Dry run (ne pas publier)", value=True)
        generate_btn = st.button("Générer", type="primary", use_container_width=True)

    with col2:
        st.subheader("Post généré")

        if generate_btn:
            with st.spinner("Génération en cours..."):
                generator = PostGenerator()

                if use_planner or not sujet:
                    planner = ContentPlanner()
                    sujet_final = planner.pick_topic(post_type)
                    st.caption(f"Sujet choisi par Claude : *{sujet_final}*")
                else:
                    sujet_final = sujet

                post = generator.generate(
                    post_type=post_type,
                    sujet=sujet_final,
                    contexte=contexte
                )

            st.text_area("Post", value=post, height=400, key="post_content")

            if st.button("Publier sur LinkedIn", type="primary"):
                with st.spinner("Vérifications en cours..."):

                    if db.already_posted_today() and not dry_run:
                        st.warning("Un post a déjà été publié aujourd'hui.")
                    elif db.is_duplicate_content(post):
                        st.warning("Ce contenu a déjà été publié. Génère un nouveau post.")
                    else:
                        with st.spinner("Publication en cours..."):
                            publisher = LinkedInPublisher()
                            succes = publisher.post(post, headless=True, dry_run=dry_run)

                            if succes:
                                if not dry_run:
                                    db.save_post(post_type, sujet_final, post)
                                    st.success("Post publié sur LinkedIn !")
                                else:
                                    st.success("Dry run réussi — post non publié")
                            else:
                                st.error("Échec de la publication")

# ─── PAGE HISTORIQUE ───
elif page == "Historique des posts":
    st.title("Historique des posts")

    posts = db.get_all_posts()

    if not posts:
        st.info("Aucun post en base.")
    else:
        for post in posts:
            with st.expander(f"{post['date']} — {post['type']} — {post['sujet'][:60]}..."):
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Likes", post["likes"])
                col2.metric("Commentaires", post["commentaires"])
                col3.metric("Republications", post["republications"])
                col4.metric("Vues", post["vues"])
                st.text(post["contenu"])
                if post.get("url"):
                    st.link_button("Voir sur LinkedIn", post["url"])