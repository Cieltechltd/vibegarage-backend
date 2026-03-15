from sqlalchemy.orm import Session
from sqlalchemy import func, desc, not_
from app.models.track import Track
from app.models.purchase import Purchase 
from app.models.playlist import Playlist, PlaylistTrack
from app.models.follow import Follow
from app.models.user import User
import random

class RecommenderService:
    @staticmethod
    def get_user_top_genres(db: Session, user_id: str, limit: int = 3):
       
        purchased_genres = (
            db.query(Track.genre, func.count(Track.genre).label("genre_count"))
            .join(Purchase, Purchase.track_id == Track.id)
            .filter(Purchase.user_id == user_id)
            .group_by(Track.genre)
        )

        playlist_genres = (
            db.query(Track.genre, func.count(Track.genre).label("genre_count"))
            .join(PlaylistTrack, PlaylistTrack.track_id == Track.id)
            .join(Playlist, Playlist.id == PlaylistTrack.playlist_id)
            .filter(Playlist.user_id == user_id)
            .group_by(Track.genre)
        )

        
        combined_counts = purchased_genres.union_all(playlist_genres).all()
        
        genre_map = {}
        for genre, count in combined_counts:
            if genre:
                genre_map[genre] = genre_map.get(genre, 0) + count
        
        sorted_genres = sorted(genre_map.items(), key=lambda x: x[1], reverse=True)
        return [g[0] for g in sorted_genres[:limit]]

    @staticmethod
    def generate_daily_mix(db: Session, user_id: str, mix_size: int = 20):
        top_genres = RecommenderService.get_user_top_genres(db, user_id)
        
        
        favorites = (
            db.query(Track)
            .join(Purchase, Purchase.track_id == Track.id)
            .filter(Purchase.user_id == user_id, Track.genre.in_(top_genres))
            .order_by(func.random())
            .limit(int(mix_size * 0.4))
            .all()
        )

        
        follows = (
            db.query(Track)
            .join(Follow, Follow.artist_id == Track.artist_id)
            .filter(Follow.follower_id == user_id)
            .order_by(desc(Track.created_at))
            .limit(int(mix_size * 0.4))
            .all()
        )

        
        owned_track_ids = db.query(Purchase.track_id).filter(Purchase.user_id == user_id)
        discovery = (
            db.query(Track)
            .join(User, Track.artist_id == User.id)
            .filter(
                Track.genre.in_(top_genres),
                not_(Track.id.in_(owned_track_ids)),
                User.is_verified_artist == False 
            )
            .order_by(func.random())
            .limit(int(mix_size * 0.2))
            .all()
        )

        
        full_mix = list(set(favorites + follows + discovery))
        random.shuffle(full_mix)
        return full_mix