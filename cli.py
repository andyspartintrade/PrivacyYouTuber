"""Privacy-YouTuber — κεντρικό CLI.

Χρήση:
    python cli.py serve        # ξεκινά τον τοπικό server (άφησέ το να τρέχει)
    python cli.py stats        # δείχνει τι έχεις καταγράψει
    python cli.py recommend    # βγάζει θέματα + ανώνυμες προτάσεις αναζήτησης
"""

import argparse
import os
import sys

# Κάνε τον φάκελο του project importable, ώστε να τρέχει από οπουδήποτε.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import db, recommender


def cmd_serve(args):
    from server import app
    db.init()
    app.serve(open_browser=args.open)


def cmd_stats(_args):
    db.init()
    vids = db.all_videos()
    print(f"📼 Βίντεο καταγεγραμμένα: {len(vids)}")
    print("-" * 60)
    for v in vids[:20]:
        cat = v["category"] or "—"
        title = (v["title"] or "")[:55]
        print(f"  • {title}  (x{v['watch_count']})  [{cat}]")
    if len(vids) > 20:
        print(f"  … και άλλα {len(vids) - 20}")


def cmd_recommend(args):
    db.init()
    vids = db.all_videos()
    if not vids:
        print("⚠️  Δεν έχεις καταγράψει τίποτα ακόμα.")
        print("   Δες μερικά βίντεο με το extension φορτωμένο, και ξανατρέξε.")
        return
    recommender.recommend(vids, top_n=args.top)


def cmd_import(args):
    from server import importer
    importer.run(args.export_dir)


def main():
    p = argparse.ArgumentParser(description="Privacy-First YouTube Recommendations")
    sub = p.add_subparsers(dest="cmd")

    srv = sub.add_parser("serve", help="run the local HTTP server")
    srv.add_argument("--open", action="store_true", help="άνοιξε το dashboard στον browser")
    sub.add_parser("stats", help="show logged videos")
    r = sub.add_parser("recommend", help="show topics + anonymous suggestions")
    r.add_argument("--top", type=int, default=5, help="πόσα θέματα να εξετάσω για προτάσεις (default 5)")
    i = sub.add_parser("import", help="import existing history from Google Takeout (JSON)")
    i.add_argument("export_dir", help="φάκελος Takeout (περιέχει watch-history.json)")

    args = p.parse_args()
    if args.cmd is None:
        # Διπλό κλικ στο .exe (ή `python cli.py` σκέτο) → server + dashboard.
        from server import app
        db.init()
        app.serve(open_browser=True)
        return
    {
        "serve": cmd_serve,
        "stats": cmd_stats,
        "recommend": cmd_recommend,
        "import": cmd_import,
    }[args.cmd](args)


if __name__ == "__main__":
    main()
