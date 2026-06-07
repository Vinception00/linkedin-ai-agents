import streamlit as st
import plotly.express as px
import pandas as pd
from dotenv import load_dotenv
from data.posts_db import PostsDB
from agent_poster.generator import PostGenerator
from agent_poster.publisher import LinkedInPublisher
from agent_poster.content_planner import ContentPlanner
from core.analytics_scrapper import AnalyticsScraper
from agent_prospector.cv_parser import CVParser
from agent_prospector.searcher import LinkedInSearcher
from agent_prospector.messenger import ProspectMessenger


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
    "Historique des posts",
    "Prospecteur"
])

# ─── PAGE DASHBOARD ───
if page == "Dashboard":
    st.title("Dashboard analytics")

    posts = db.get_all_posts()

    if not posts:
        st.info("Aucun post en base. Publie ton premier post dans 'Générer un post'.")
    else:
        df = pd.DataFrame(posts)

        # Nettoie les titres (enlève le markdown résiduel)
        import re as _re
        df["sujet_clean"] = df["sujet"].apply(lambda s: _re.sub(r'\*{1,2}', '', str(s)).strip())

        # Label court pour les graphiques : date · type
        df["label"] = df["date"].astype(str) + " · " + df["type"]

        # ── KPIs ──
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Posts publiés", len(df))
        col2.metric("Total likes", int(df["likes"].sum()))
        col3.metric("Total commentaires", int(df["commentaires"].sum()))
        col4.metric("Total vues", int(df["vues"].sum()))

        st.divider()

        has_stats = int(df["likes"].sum() + df["vues"].sum()) > 0

        if not has_stats:
            st.info("Les stats sont à 0 pour l'instant. Va dans Historique pour scraper l'engagement de tes posts.")
        else:
            col1, col2 = st.columns(2)

            with col1:
                # Barres horizontales : meilleurs posts par likes
                df_sorted = df.sort_values("likes", ascending=True)
                fig = px.bar(
                    df_sorted,
                    y="label",
                    x="likes",
                    orientation="h",
                    color="type",
                    title="Likes par post",
                    custom_data=["sujet_clean"]
                )
                fig.update_traces(
                    hovertemplate="<b>%{customdata[0]}</b><br>Likes : %{x}<extra></extra>"
                )
                fig.update_layout(
                    yaxis_title="",
                    xaxis_title="Likes",
                    showlegend=False,
                    margin=dict(l=10, r=10, t=40, b=10)
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Ligne d'évolution des likes dans le temps
                df["date_dt"] = pd.to_datetime(df["date"])
                df_time = df.sort_values("date_dt")
                fig2 = px.line(
                    df_time,
                    x="date_dt",
                    y="likes",
                    markers=True,
                    color="type",
                    title="Évolution des likes",
                    custom_data=["sujet_clean", "label"]
                )
                fig2.update_traces(
                    hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>Likes : %{y}<extra></extra>"
                )
                fig2.update_layout(
                    xaxis_title="",
                    yaxis_title="Likes",
                    margin=dict(l=10, r=10, t=40, b=10)
                )
                st.plotly_chart(fig2, use_container_width=True)

        st.divider()

        # ── Tableau détaillé ──
        st.subheader("Tous les posts")
        df_display = df[["date", "type", "sujet_clean", "likes", "commentaires", "republications", "vues"]].copy()
        df_display = df_display.rename(columns={"sujet_clean": "sujet"})
        df_display = df_display.sort_values("date", ascending=False)
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "sujet": st.column_config.TextColumn("Sujet", width="large"),
                "likes": st.column_config.NumberColumn("Likes"),
                "commentaires": st.column_config.NumberColumn("Commentaires"),
                "republications": st.column_config.NumberColumn("Reposts"),
                "vues": st.column_config.NumberColumn("Vues"),
            }
        )

# ─── PAGE GÉNÉRER UN POST ───
elif page == "Générer un post":
    st.title("Générer un post LinkedIn")

    # Initialise la session state
    if "post_genere" not in st.session_state:
        st.session_state.post_genere = None
    if "sujet_final" not in st.session_state:
        st.session_state.sujet_final = None
    if "post_type_final" not in st.session_state:
        st.session_state.post_type_final = None

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
                    st.session_state.sujet_final = planner.pick_topic(post_type)
                    st.caption(f"Sujet choisi par Claude : *{st.session_state.sujet_final}*")
                else:
                    st.session_state.sujet_final = sujet

                st.session_state.post_type_final = post_type
                st.session_state.post_genere = generator.generate(
                    post_type=post_type,
                    sujet=st.session_state.sujet_final,
                    contexte=contexte
                )

        if st.session_state.post_genere:
            post_edite = st.text_area(
                "Post (modifiable avant publication)",
                value=st.session_state.post_genere,
                height=400,
                key="post_content"
            )

            if st.button("Publier sur LinkedIn", type="primary"):
                with st.spinner("Vérifications en cours..."):
                    if db.already_posted_today() and not dry_run:
                        st.warning("Un post a déjà été publié aujourd'hui.")
                    elif db.is_duplicate_content(post_edite):
                        st.warning("Ce contenu a déjà été publié. Génère un nouveau post.")
                    else:
                        with st.spinner("Publication en cours..."):
                            publisher = LinkedInPublisher()
                            succes, post_url = publisher.post(post_edite, headless=False, dry_run=dry_run)

                            if succes:
                                if not dry_run:
                                    db.save_post(
                                        st.session_state.post_type_final,
                                        st.session_state.sujet_final,
                                        post_edite,
                                        url=post_url
                                    )
                                    st.success("Post publié sur LinkedIn !")
                                    if post_url:
                                        st.link_button("Voir le post", post_url)
                                    st.session_state.post_genere = None
                                else:
                                    st.success("Dry run réussi — post non publié")
                            else:
                                st.error("Échec de la publication")

# ─── PAGE HISTORIQUE ───
elif page == "Historique des posts":
    import re as _re

    st.title("Historique des posts")

    posts = db.get_all_posts()

    if not posts:
        st.info("Aucun post en base.")
    else:
        # Sync depuis la page d'activité (récupère tout en une fois)
        scraper_tmp = AnalyticsScraper()
        default_username = scraper_tmp.extract_username_from_db() or ""

        col_user, col_sync, col_debug = st.columns([3, 2, 1])
        username_input = col_user.text_input(
            "Ton username LinkedIn",
            value=default_username,
            placeholder="prenom-nom-123456789",
            label_visibility="collapsed"
        )
        debug_mode = col_debug.checkbox("Debug", value=False)

        if col_sync.button("Sync depuis LinkedIn", type="primary") and username_input:
            with st.spinner(f"Récupération depuis /in/{username_input}/recent-activity..."):
                try:
                    scraper = AnalyticsScraper()
                    n = scraper.sync_from_activity_page(username_input)
                    st.success(f"{n} post(s) mis à jour")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")

        st.divider()

        for post in posts:
            sujet_clean = _re.sub(r'\*{1,2}', '', post["sujet"]).strip()
            titre_expander = f"{post['date']} · {post['type']} · {sujet_clean[:55]}{'...' if len(sujet_clean) > 55 else ''}"

            with st.expander(titre_expander):
                # URL en premier — visible sans scroller
                if post.get("url"):
                    col_lien, col_refresh, _ = st.columns([2, 2, 3])
                    col_lien.link_button("Voir sur LinkedIn", post["url"])
                    if col_refresh.button("Rafraîchir les stats", key=f"refresh_{post['id']}"):
                        with st.spinner("Scraping..."):
                            try:
                                scraper = AnalyticsScraper()
                                scraper.scrape_post_stats(post["url"], post["id"], debug=debug_mode)
                                st.success("Stats mises à jour")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erreur : {e}")
                else:
                    col_input, col_save = st.columns([4, 1])
                    new_url = col_input.text_input(
                        "URL LinkedIn du post",
                        placeholder="https://www.linkedin.com/posts/...",
                        label_visibility="collapsed",
                        key=f"url_input_{post['id']}"
                    )
                    if col_save.button("Enregistrer l'URL", key=f"save_url_{post['id']}") and new_url:
                        try:
                            scraper = AnalyticsScraper()
                            scraper.update_post_url(post["id"], new_url)
                            st.success("URL enregistrée — tu peux maintenant rafraîchir les stats")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {e}")

                st.divider()

                # Stats
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Likes", post["likes"])
                col2.metric("Commentaires", post["commentaires"])
                col3.metric("Reposts", post["republications"])
                col4.metric("Vues", post["vues"])
                if post.get("scraped_at"):
                    st.caption(f"Stats au {post['scraped_at'][:16]}")

                # Contenu en hauteur fixe, scrollable
                st.text_area(
                    "Contenu publié",
                    value=post["contenu"],
                    height=160,
                    disabled=True,
                    key=f"content_{post['id']}"
                )

# ─── PAGE PROSPECTEUR ───
elif page == "Prospecteur":
    st.title("Agent Prospecteur LinkedIn")
    st.caption("Parse ton CV, recherche des profils LinkedIn, génère des messages personnalisés.")

    # Session state
    if "cv_profil" not in st.session_state:
        st.session_state.cv_profil = None
    if "prospects" not in st.session_state:
        st.session_state.prospects = []
    if "messages_generes" not in st.session_state:
        st.session_state.messages_generes = []

    # ── Étape 1 : Upload du CV ──
    st.subheader("Étape 1 — Charger ton CV")

    col1, col2 = st.columns([1, 1])

    with col1:
        uploaded_cv = st.file_uploader("Importe ton CV (PDF)", type=["pdf"])
        if uploaded_cv and st.button("Parser le CV", type="primary"):
            with st.spinner("Lecture du CV via Claude..."):
                try:
                    import tempfile, os
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                        tmp.write(uploaded_cv.read())
                        tmp_path = tmp.name
                    parser = CVParser()
                    st.session_state.cv_profil = parser.parse(tmp_path)
                    os.unlink(tmp_path)
                    st.success("CV parsé avec succès !")
                except Exception as e:
                    st.error(f"Erreur parsing CV : {e}")

    with col2:
        if st.session_state.cv_profil:
            p = st.session_state.cv_profil
            st.markdown(f"**{p.get('nom', '—')}** — {p.get('titre', '—')}")
            if p.get("email"):
                st.caption(f"Email : {p['email']}")
            if p.get("competences"):
                st.markdown("**Compétences :** " + ", ".join(p["competences"][:8]))
            if p.get("resume"):
                st.info(p["resume"])

    if not st.session_state.cv_profil:
        st.stop()

    st.divider()

    # ── Étape 2 : Recherche LinkedIn ──
    st.subheader("Étape 2 — Rechercher des profils LinkedIn")

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        keywords = st.text_input(
            "Mots-clés de recherche",
            placeholder="Ex: Data Scientist Paris, ML Engineer, Recruteur Tech"
        )
    with col2:
        max_results = st.number_input("Nb résultats", min_value=1, max_value=20, value=5)
    with col3:
        degree = st.selectbox("Degré connexion", ["2", "1", "3"],
                              format_func=lambda x: {"1": "1er", "2": "2ème", "3": "3ème+"}[x])

    if st.button("Rechercher sur LinkedIn", type="primary") and keywords:
        with st.spinner("Recherche en cours (connexion LinkedIn...)"):
            try:
                searcher = LinkedInSearcher()
                st.session_state.prospects = searcher.search_people(
                    keywords=keywords,
                    max_results=int(max_results),
                    degree=degree
                )
                st.session_state.messages_generes = []
            except Exception as e:
                st.error(f"Erreur recherche : {e}")

    if st.session_state.prospects:
        st.success(f"{len(st.session_state.prospects)} profils trouvés")
        df_prospects = pd.DataFrame(st.session_state.prospects)
        st.dataframe(df_prospects, use_container_width=True, hide_index=True)
    elif st.session_state.prospects == []:
        st.info("Aucun résultat. Vérifie les mots-clés ou ta connexion LinkedIn.")

    if not st.session_state.prospects:
        st.stop()

    st.divider()

    # ── Étape 3 : Générer des messages ──
    st.subheader("Étape 3 — Générer des messages personnalisés")

    col1, col2 = st.columns(2)
    with col1:
        mode_msg = st.radio("Type de message", ["connexion", "inmail"], horizontal=True,
                            format_func=lambda x: "Invitation (≤300 chars)" if x == "connexion" else "InMail (long)")
        objectif_msg = st.selectbox("Objectif", ["networking", "emploi", "collaboration"])
    with col2:
        details_msg = st.text_area(
            "Contexte supplémentaire (optionnel)",
            placeholder="Ex : je postule au poste de Data Analyst chez votre entreprise...",
            height=80
        )

    if st.button("Générer les messages", type="primary"):
        with st.spinner("Génération via Claude..."):
            try:
                messenger = ProspectMessenger()
                st.session_state.messages_generes = messenger.generate_batch(
                    mon_profil=st.session_state.cv_profil,
                    cibles=st.session_state.prospects,
                    mode=mode_msg,
                    objectif=objectif_msg,
                    details=details_msg
                )
                st.success("Messages générés !")
            except Exception as e:
                st.error(f"Erreur génération : {e}")

    if st.session_state.messages_generes:
        for item in st.session_state.messages_generes:
            profil = item["profil"]
            message = item["message"]
            label = f"{profil.get('nom', '?')} — {profil.get('titre', '')} @ {profil.get('entreprise', '')}"
            with st.expander(label):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text_area("Message", value=message, height=150, key=f"msg_{profil.get('url', profil.get('nom', ''))}")
                with col2:
                    if mode_msg == "connexion":
                        chars = len(message)
                        color = "green" if chars <= 300 else "red"
                        st.markdown(f"**Caractères :** :{color}[{chars}/300]")
                    if profil.get("url"):
                        st.link_button("Voir profil", profil["url"])