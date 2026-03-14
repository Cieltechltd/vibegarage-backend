def get_welcome_html(user_name: str, is_verified: bool = False):
    badge = '<span style="color: #800000; margin-left: 5px;">✔</span>' if is_verified else ""
    
    return f"""
    <html>
        <body style="font-family: 'Georgia', serif; line-height: 1.8; color: #1a1a1a; background-color: #f4f4f4; padding: 40px 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #ffffff; padding: 50px; border-radius: 8px; box-shadow: 0 15px 40px rgba(0,0,0,0.1); border-top: 6px solid #800000;">
                
                <h1 style="font-size: 26px; font-weight: 400; color: #000; letter-spacing: -1px; margin-bottom: 25px;">
                    The Garage is open, {user_name}{badge}.
                </h1>

                <p style="font-size: 16px; margin-bottom: 20px;">
                    I am <strong>Utibe-Abasi Jacob Udoh</strong>—though most people in this industry know me simply as <strong>Utee Jacob</strong>. I’m a builder, a dreamer, and the founder of this movement. My life has been dedicated to the intersection of sound and systems, but more importantly, to the artists who refuse to be ignored.
                </p>

                <p style="font-size: 16px; margin-bottom: 30px;">
                    <strong>Vibe Garage</strong> is the digital home for the loud and the brave. We didn’t build this to be just another "platform." We built it to be a sanctuary—a place where raw creative energy is refined into a global force, and where the creator finally holds the keys to their own kingdom.
                </p>

                <div style="padding: 25px; background: #fafafa; border-left: 3px solid #D4AF37; margin-bottom: 35px;">
                    <p style="margin: 0; font-style: italic; color: #444;">
                        "The experience started in <strong>Port Harcourt</strong>, late 2017. I met <a href="https://www.youtube.com/@chaleedip" style="color: #800000; text-decoration: underline; font-weight: bold;">Chalee Dip</a>, and we realized the same thing: the sound of the streets was being lost in the noise of the industry. We launched <strong>MusicPort Nigeria</strong> with nothing but a shared obsession to fix it."
                    </p>
                </div>

                <p>We spent seven years in the trenches, moving from the heartbeat of PH to a vision that now spans the globe. We saw the highs, the silence of the nights when the dream felt too heavy, and the evolution of MusicPort into what you see today: <strong>Vibe Garage</strong>. This is the culmination of that sweat, that grit, and that refusal to back down.</p>
                
                <p>You aren't just a user. You are the hero of the story we’ve been writing since 2017. The world is finally ready to hear you.</p>

                <div style="margin: 45px 0; text-align: center;">
                    <a href="https://vibegarage.app/upload" style="background: linear-gradient(135deg, #D4AF37 0%, #800000 100%); color: #ffffff; padding: 20px 40px; text-decoration: none; font-family: 'Helvetica', sans-serif; font-size: 15px; font-weight: bold; letter-spacing: 2px; display: inline-block; border-radius: 4px; box-shadow: 0 4px 15px rgba(128, 0, 0, 0.3);">CLAIM YOUR THRONE</a>
                </div>

                <p style="margin-top: 50px; font-size: 15px;">Respect the craft,</p>
                
                <p style="line-height: 1.2;">
                    <strong>Utee Jacob</strong><br>
                    <span style="font-size: 11px; color: #999; text-transform: uppercase; letter-spacing: 1px;">Founder, Vibe Garage Entertainment</span>
                    
                </p>
                
                 <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0;">

                <p style="font-size: 13px; color: #888; text-align: center;">

                    Follow the Evolution:<br>

                    <a href="https://www.instagram.com/vibegarage_entertainment" style="margin: 0 10px; color: #555;">Instagram</a> | 

                    <a href="https://x.com/VibeGarage" style="margin: 0 10px; color: #555;">X (Twitter)</a> | 

                    <a href="https://www.facebook.com/VibeGarage" style="margin: 0 10px; color: #555;">Facebook</a> |

                    <a href="https://cieltech.org" style="margin: 0 10px; color: #555;">Ciel Tech</a>

                </p>
                
                <hr style="border: 0; border-top: 1px solid #eee; margin: 40px 0;">
                
                <p style="font-size: 10px; color: #ccc; text-align: center; text-transform: uppercase; letter-spacing: 3px;">
                    EST. 2017 | PORT HARCOURT TO THE WORLD
                </p>
            </div>
        </body>
    </html>
    """