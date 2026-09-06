import os
import wave
import math
import struct
from datetime import datetime, timedelta
try:
    from .database import engine, Base, SessionLocal
    from .models import Admin, Settings, Music, PromoCode, OrderInquiry, AlertPopup, AboutSection, Slide, Category
    from .auth import hash_password
except (ImportError, ValueError):
    from database import engine, Base, SessionLocal
    from models import Admin, Settings, Music, PromoCode, OrderInquiry, AlertPopup, AboutSection, Slide, Category
    from auth import hash_password

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def generate_melodic_audio(filepath: str, base_freq: float = 300, duration: int = 15, style: str = "acoustic"):
    """Generates a pleasant 15-second melodic preview WAV file"""
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    with wave.open(filepath, "w") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        
        # Pentatonic scale offsets
        scale = [1.0, 1.125, 1.25, 1.5, 1.667, 2.0]
        
        for i in range(n_samples):
            t = i / sample_rate
            note_idx = int(t * 2) % len(scale)
            freq = base_freq * scale[note_idx]
            
            # Base synth
            v1 = math.sin(2 * math.pi * freq * t)
            v2 = 0.5 * math.sin(2 * math.pi * (freq * 2.0) * t)
            v3 = 0.25 * math.sin(2 * math.pi * (freq * 0.5) * t)
            
            # Rhythm / pulse
            pulse = 0.7 + 0.3 * math.sin(2 * math.pi * 4 * t)
            envelope = min(1.0, (duration - t) / 2.0) if t > duration - 2 else min(1.0, t * 1.5)
            
            val = int((v1 + v2 + v3) / 2.5 * pulse * envelope * 22000)
            wav.writeframesraw(struct.pack("<hh", val, val))

def create_default_logo():
    logo_path = os.path.join(UPLOAD_DIR, "logo.svg")
    if not os.path.exists(logo_path):
        svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 60" width="200" height="60">
  <defs>
    <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#EC4899;stop-opacity:1" />
      <stop offset="50%" style="stop-color:#8B5CF6;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#3B82F6;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect x="5" y="10" width="40" height="40" rx="12" fill="url(#grad1)" />
  <circle cx="25" cy="30" r="12" fill="#0F172A" />
  <path d="M22 23 L22 35 M22 25 Q28 22 28 29 Q28 35 22 35" fill="none" stroke="#EC4899" stroke-width="2.5" stroke-linecap="round"/>
  <circle cx="20" cy="34" r="3" fill="#EC4899" />
  <text x="56" y="32" font-family="system-ui, -apple-system, sans-serif" font-weight="800" font-size="20" fill="#FFFFFF">KHMER</text>
  <text x="135" y="32" font-family="system-ui, -apple-system, sans-serif" font-weight="800" font-size="20" fill="#EC4899">BEATS</text>
  <text x="57" y="46" font-family="system-ui, -apple-system, sans-serif" font-weight="500" font-size="11" fill="#94A3B8">PREMIUM SOUNDS</text>
</svg>"""
        with open(logo_path, "w") as f:
            f.write(svg_content)

def seed_database():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        create_default_logo()

        # 1. Admin
        default_user = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
        default_pass = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
        admin = db.query(Admin).filter(Admin.username == default_user).first()
        if not admin:
            admin = Admin(
                username=default_user,
                password_hash=hash_password(default_pass)
            )
            db.add(admin)
            print(f"Default admin initialized: {default_user}")

        # 2. Settings
        settings = db.query(Settings).first()
        if not settings:
            settings = Settings(
                site_name_en="KhmerBeats Store",
                site_name_kh="ហាងតន្ត្រី ខ្មែរប៊ីត",
                logo_url="/uploads/logo.svg",
                telegram_username="music_admin_kh",
                telegram_channel="https://t.me/khmerbeats_channel",
                currency_symbol="$",
                contact_phone="+855 12 888 999",
                banner_title_en="Buy Original Khmer & International Music",
                banner_title_kh="ទិញបទចម្រៀង Original និងតន្ត្រីពិរោះៗ",
                banner_sub_en="Instant purchase via Telegram with zero registration. Support local artists directly!",
                banner_sub_kh="ទិញភ្លាមៗតាម Telegram ដោយមិនបាច់ចុះឈ្មោះ។ គាំទ្រស្នាដៃសិល្បករខ្មែរផ្ទាល់!"
            )
            db.add(settings)
            print("Default settings created")

        # 3. Promo Codes
        promos = [
            PromoCode(
                code="WELCOME10",
                discount_type="percent",
                discount_value=10.0,
                min_spend=5.0,
                max_discount=10.0,
                expires_at=datetime.utcnow() + timedelta(days=90),
                is_active=True
            ),
            PromoCode(
                code="KHMER2026",
                discount_type="percent",
                discount_value=20.0,
                min_spend=8.0,
                max_discount=25.0,
                expires_at=datetime.utcnow() + timedelta(days=180),
                is_active=True
            ),
            PromoCode(
                code="SUPER5",
                discount_type="fixed",
                discount_value=5.0,
                min_spend=15.0,
                expires_at=datetime.utcnow() + timedelta(days=60),
                is_active=True
            )
        ]
        for p in promos:
            if not db.query(PromoCode).filter(PromoCode.code == p.code).first():
                db.add(p)
        print("Promo codes seeded")

        # 3.5 Alert Popup (Announcement)
        existing_alert = db.query(AlertPopup).first()
        if not existing_alert:
            default_alert = AlertPopup(
                title_en="Special Khmer Music Promotion 2026",
                title_kh="ប្រូម៉ូសិនពិសេសសម្រាប់តន្ត្រីខ្មែរ ២០២៦",
                message_en="Get up to 50% discount on all original Khmer tracks this month! Use promo code KHMER2026 at checkout or directly contact admin on Telegram.",
                message_kh="ទទួលបានការបញ្ចុះតម្លៃរហូតដល់ 50% លើគ្រប់បទចម្រៀង Original ខ្មែរក្នុងខែនេះ! ប្រើកូដ KHMER2026 ពេលកុម្ម៉ង់ទិញ ឬទាក់ទង Admin តាម Telegram។",
                date="2026-09-06",
                expire_date="2026-12-31",
                badge_en="Grand Promo",
                badge_kh="ប្រូម៉ូសិនធំ",
                link_url="#catalog",
                link_text_en="Explore Tracks",
                link_text_kh="ស្វែងរកបទចម្រៀង",
                is_active=True
            )
            db.add(default_alert)
            print("Default alert popup seeded")

        # 3.8 About Us Content
        if db.query(AboutSection).count() == 0:
            sample_abouts = [
                AboutSection(
                    title_en="Our Passion for Khmer Music",
                    title_kh="ទឹកចិត្តស្រឡាញ់តន្ត្រីខ្មែររបស់យើង",
                    subtitle_en="Empowering Creators & Preserving Heritage",
                    subtitle_kh="លើកកម្ពស់អ្នកបង្កើត និងថែរក្សាកេរដំណែល",
                    content_en="KhmerBeats is Cambodia's premier digital music platform dedicated to showcasing authentic original tracks, traditional fusions, and modern sounds from talented local producers.",
                    content_kh="ហាងតន្ត្រី ខ្មែរប៊ីត គឺជាវេទិកាតន្ត្រីឌីជីថលឈានមុខគេនៅកម្ពុជា ដែលផ្តោតលើការបង្ហាញស្នាដៃបទចម្រៀង Original ពិតៗ តន្ត្រីបុរាណច្នៃប្រឌិត និងចង្វាក់ទំនើបពីផលិតករខ្មែរ។",
                    image_url="https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=800&auto=format&fit=crop&q=80",
                    badge_en="Our Story",
                    badge_kh="រឿងរ៉ាវរបស់យើង",
                    order_index=1,
                    is_active=True
                ),
                AboutSection(
                    title_en="Direct Support for Local Artists",
                    title_kh="ការគាំទ្រដោយផ្ទាល់ដល់សិល្បករខ្មែរ",
                    subtitle_en="Instant Telegram Checkout with 100% Transparency",
                    subtitle_kh="ទិញភ្លាមៗតាម Telegram ប្រកបដោយតម្លាភាព ១០០%",
                    content_en="When you purchase music through KhmerBeats, the proceeds directly support independent Cambodian artists and audio engineers with zero registration barriers.",
                    content_kh="រាល់ការទិញបទចម្រៀងលើ ខ្មែរប៊ីត ប្រាក់ចំណូលគឺគាំទ្រផ្ទាល់ដល់សិល្បករ និងអ្នកផលិតតន្ត្រីឯករាជ្យនៅកម្ពុជា ដោយមិនចាំបាច់មានការចុះឈ្មោះស្មុគស្មាញឡើយ។",
                    image_url="https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=800&auto=format&fit=crop&q=80",
                    badge_en="Our Mission",
                    badge_kh="បេសកកម្មរបស់យើង",
                    order_index=2,
                    is_active=True
                ),
                AboutSection(
                    title_en="Studio Quality Mastered Audio",
                    title_kh="គុណភាពសំឡេងកម្រិតស្ទូឌីយោ",
                    subtitle_en="High-Fidelity Lossless Sound with Free Previews",
                    subtitle_kh="សំឡេងច្បាស់ល្អឥតខ្ចោះ អាចស្ដាប់សាកល្បងដោយសេរី",
                    content_en="Every single track available on our store is mastered to industry broadcast standards, complete with high-resolution album artwork and lyrics.",
                    content_kh="គ្រប់បទចម្រៀងទាំងអស់ត្រូវបានកែសម្រួល Master តាមស្តង់ដារស្ទូឌីយោកម្រិតខ្ពស់ រួមជាមួយរូបភាព Album Art និងទំនុកច្រៀងត្រឹមត្រូវ។",
                    image_url="https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=800&auto=format&fit=crop&q=80",
                    badge_en="Quality Guarantee",
                    badge_kh="ការធានាគុណភាព",
                    order_index=3,
                    is_active=True
                )
            ]
            for a in sample_abouts:
                db.add(a)
            print("Default about sections seeded")

        # 4. Generate preview audio files & sample tracks
        audio_files = [
            ("preview_acoustic.wav", 220.0),
            ("preview_lofi.wav", 261.63),
            ("preview_pop.wav", 293.66),
            ("preview_synthwave.wav", 329.63),
            ("preview_traditional.wav", 349.23),
            ("preview_edm.wav", 392.00),
        ]
        for fname, freq in audio_files:
            fpath = os.path.join(UPLOAD_DIR, fname)
            if not os.path.exists(fpath):
                generate_melodic_audio(fpath, base_freq=freq, duration=15)

        # 5. Sample Music Tracks
        sample_tracks = [
            {
                "title_en": "Moonlight over Angkor",
                "title_kh": "ពន្លឺចន្ទលើអង្គរ",
                "artist_en": "VannDa & Khmer Traditional Ensemble",
                "artist_kh": "វណ្ណដា និងក្រុមតន្ត្រីបុរាណ",
                "genre": "Hip Hop / Fusion",
                "price": 12.0,
                "discount_percent": 25.0,
                "cover_image_url": "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=600&auto=format&fit=crop&q=80",
                "preview_audio_url": "/uploads/preview_traditional.wav",
                "description_en": "Mesmerizing blend of ancient Khmer instruments with modern 808 hip hop beats.",
                "description_kh": "បទភ្លេងកែច្នៃរួមបញ្ចូលឧបករណ៍បុរាណខ្មែរជាមួយចង្វាក់ Hip Hop ទំនើបដ៏រំជើបរំជួល។",
                "duration": "3:42",
                "is_featured": True
            },
            {
                "title_en": "Battambang Memories",
                "title_kh": "អនុស្សាវរីយ៍បាត់ដំបង",
                "artist_en": "Sinn Sisamouth Tribute (Remastered)",
                "artist_kh": "រំលឹកគុណ ស៊ិន ស៊ីសាមុត (Remastered)",
                "genre": "Classic Khmer",
                "price": 8.0,
                "discount_percent": 15.0,
                "cover_image_url": "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=600&auto=format&fit=crop&q=80",
                "preview_audio_url": "/uploads/preview_acoustic.wav",
                "description_en": "A remastered romantic classic bringing nostalgic golden era melodies to 2026.",
                "description_kh": "បទចម្រៀងមនោសញ្ចេតនាយុគមាសខ្មែរដ៏ល្បីល្បាញ ដែលបានកែសម្រួលគុណភាពសំឡេងកម្រិតខ្ពស់។",
                "duration": "4:15",
                "is_featured": True
            },
            {
                "title_en": "Phnom Penh Cyber Nights",
                "title_kh": "រាត្រីភ្នំពេញស៊ីវិល័យ",
                "artist_en": "DJ Sopheak",
                "artist_kh": "ឌីជេ សុភ័ក្ត្រ",
                "genre": "Synthwave / EDM",
                "price": 10.0,
                "discount_percent": 20.0,
                "cover_image_url": "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=600&auto=format&fit=crop&q=80",
                "preview_audio_url": "/uploads/preview_synthwave.wav",
                "description_en": "Electrifying nightlife synthwave inspired by the glowing skyline of Phnom Penh.",
                "description_kh": "ភ្លេងបែប Synthwave ទំនើប ឆ្លុះបញ្ចាំងពីសម្រស់ពន្លឺភ្លើងរាត្រីនៃរាជធានីភ្នំពេញ។",
                "duration": "3:30",
                "is_featured": True
            },
            {
                "title_en": "Koh Rong Sunset Chill",
                "title_kh": "ថ្ងៃលិចកោះរ៉ុងដ៏សែនស្ងប់",
                "artist_en": "Acoustic Horizon",
                "artist_kh": "ក្រុមតន្ត្រី អាកូស្ទីក ហ័ររីហ្សិន",
                "genre": "Acoustic / Lo-Fi",
                "price": 6.0,
                "discount_percent": 0.0,
                "cover_image_url": "https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=600&auto=format&fit=crop&q=80",
                "preview_audio_url": "/uploads/preview_lofi.wav",
                "description_en": "Gentle acoustic guitar and ocean waves for relaxation, study, and meditation.",
                "description_kh": "សំឡេងហ្គីតាអាកូស្ទីកដ៏ផ្អែមល្ហែម សម្រាប់ស្ដាប់លម្ហែកាយ និងសម្រាកអារម្មណ៍។",
                "duration": "2:58",
                "is_featured": False
            },
            {
                "title_en": "Siem Reap Morning Breeze",
                "title_kh": "ខ្យល់ជំនោរព្រឹកព្រលឹមសៀមរាប",
                "artist_en": "Bopha & The Rhythm",
                "artist_kh": "បុប្ផា & ដឺ រីតឹម",
                "genre": "Pop / Indie",
                "price": 7.5,
                "discount_percent": 10.0,
                "cover_image_url": "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=600&auto=format&fit=crop&q=80",
                "preview_audio_url": "/uploads/preview_pop.wav",
                "description_en": "Uplifting indie pop song with catchy vocal hooks and acoustic rhythm.",
                "description_kh": "បទចម្រៀង Pop ស្រស់ស្រាយ បង្កើនថាមពលវិជ្ជមាននាពេលព្រឹក។",
                "duration": "3:18",
                "is_featured": False
            },
            {
                "title_en": "Bass of Bokor Mountain",
                "title_kh": "ចង្វាក់បាស់ភ្នំបូកគោ",
                "artist_en": "Kampot Bass Crew",
                "artist_kh": "ក្រុមតន្ត្រី កំពតបាស់គ្រូ",
                "genre": "Bass / Trap",
                "price": 9.0,
                "discount_percent": 30.0,
                "cover_image_url": "https://images.unsplash.com/photo-1465847899084-d164df4dedc6?w=600&auto=format&fit=crop&q=80",
                "preview_audio_url": "/uploads/preview_edm.wav",
                "description_en": "Heavy sub-bass festival track with mountain mist atmosphere.",
                "description_kh": "បទចង្វាក់ Bass ធ្ងន់ៗកន្ត្រាក់អារម្មណ៍ សម្រាប់ពិធីជប់លៀង និងកម្មវិធីសប្បាយៗ។",
                "duration": "3:55",
                "is_featured": True
            }
        ]

        for t in sample_tracks:
            existing = db.query(Music).filter(Music.title_en == t["title_en"]).first()
            if not existing:
                music_item = Music(**t)
                db.add(music_item)
        
        # Seed Slides
        sample_slides = [
            {
                "title_en": "Khmer Original Beats & Studio Masters",
                "title_kh": "តន្ត្រីខ្មែរ Original & សំឡេងកម្រិតស្ទូឌីយោ",
                "subtitle_en": "Direct support for independent Cambodian musicians and producers with instant Telegram checkout.",
                "subtitle_kh": "គាំទ្រផ្ទាល់ដល់អ្នកផលិតតន្ត្រីខ្មែរឯករាជ្យ ទិញភ្លាមបានភ្លាមតាម Telegram ដោយមិនចាំបាច់ចុះឈ្មោះ។",
                "badge_en": "Featured Release",
                "badge_kh": "បទចេញថ្មីពិសេស",
                "media_type": "image",
                "media_url": "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=1600&auto=format&fit=crop&q=85",
                "thumbnail_url": "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=600&auto=format&fit=crop&q=80",
                "link_url": "#/products",
                "link_text_en": "Listen & Buy",
                "link_text_kh": "ស្ដាប់ និងទិញឥឡូវនេះ",
                "order_index": 1,
                "is_active": True
            },
            {
                "title_en": "Angkor Electronic & Traditional Fusion",
                "title_kh": "តន្ត្រីអេឡិចត្រូនិកច្នៃប្រឌិតជាមួយឧបករណ៍បុរាណខ្មែរ",
                "subtitle_en": "Experience the magical blend of Roneat, Chapei Dong Veng, and modern electronic basslines.",
                "subtitle_kh": "បទពិសោធន៍ថ្មីនៃការរួមបញ្ចូលគ្នារវាងឧបករណ៍ភ្លេងបុរាណ និងចង្វាក់ Bass ទំនើបកន្ត្រាក់អារម្មណ៍។",
                "badge_en": "Live Video Showcase",
                "badge_kh": "វីដេអូតន្ត្រីបន្តផ្ទាល់",
                "media_type": "youtube",
                "media_url": "https://www.youtube.com/watch?v=ScMzIvxBSi4",
                "thumbnail_url": "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=600&auto=format&fit=crop&q=80",
                "link_url": "#/products",
                "link_text_en": "Explore Tracks",
                "link_text_kh": "ស្វែងរកបទចម្រៀង",
                "order_index": 2,
                "is_active": True
            },
            {
                "title_en": "Studio Recording & Sound Design Sessions",
                "title_kh": "ទិដ្ឋភាពថតសម្លេងក្នុងស្ទូឌីយោកម្រិតខ្ពស់",
                "subtitle_en": "Lossless 320kbps MP3 & 24-bit WAV audio files ready for broadcast and personal listening.",
                "subtitle_kh": "ឯកសារសំឡេងច្បាស់ល្អឥតខ្ចោះ 320kbps MP3 & WAV ស្តង់ដារផ្សាយអន្តរជាតិ។",
                "badge_en": "Studio Session",
                "badge_kh": "កម្រិតស្ទូឌីយោ",
                "media_type": "video",
                "media_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
                "thumbnail_url": "https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=1200&auto=format&fit=crop&q=80",
                "link_url": "#/about",
                "link_text_en": "About Our Studio",
                "link_text_kh": "អំពីស្ទូឌីយោរបស់យើង",
                "order_index": 3,
                "is_active": True
            }
        ]

        for s in sample_slides:
            existing = db.query(Slide).filter(Slide.title_en == s["title_en"]).first()
            if not existing:
                slide_item = Slide(**s)
                db.add(slide_item)

        db.commit()
        print("Database seeded successfully with sample music, about, and slides!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
