//! Piclines: what makes this build the Piclines Editor (piclines/README.md).
//!
//! Our changes to the Rust code live here and in `app/view/piclines.rs`. Upstream's
//! files only call in, at lines marked `// Piclines:`, so upstream's new releases merge
//! with few conflicts.

pub const NAME: &str = "Piclines Editor";
/// Where help lives: Piclines' questions.
pub const HELP: &str = "https://piclines.com/#questions";
/// Feedback and problem reports go to Piclines' support, by mail.
pub const SUPPORT: &str = "mailto:support@piclines.com";
/// The editor's source, as the GPL asks (§6): our public fork.
pub const SOURCE: &str = "https://github.com/azizisahand/piclines-editor";

/// Links of the original project the app may still offer somewhere (and new ones a later
/// release may add): its issue tracker becomes our support mail; its other pages —
/// GitHub, sponsors, donations, videos, forums — are not opened at all.
const ISSUES: &str = "github.com/hakanseven12/opencadstudio/issues";
const BLOCKED: &[&str] = &[
    "github.com/hakanseven12",
    "hakanseven12.github.io",
    "raw.githubusercontent.com/hakanseven12",
    "opencadstudio.com",
    "patreon.com",
    "reddit.com/r/opencadstudio",
    "open-aec.com",
    "youtube.com",
    "youtu.be",
];

/// The link to open instead of `url`: our own for upstream's issues, `None` for any other
/// page of the original project, else `url` itself.
pub fn link(url: &str) -> Option<String> {
    let lower = url.to_ascii_lowercase();
    if lower.contains(ISSUES) {
        return Some(SUPPORT.to_string());
    }
    if BLOCKED.iter().any(|blocked| lower.contains(blocked)) {
        return None;
    }
    Some(url.to_string())
}

/// Piclines' colours ("Night Vector") as the app's default theme. Users can still pick
/// any other in Options.
pub fn seed() -> iced::theme::palette::Seed {
    let rgb = |hex: u32| iced::Color::from_rgb8((hex >> 16) as u8, (hex >> 8) as u8, hex as u8);
    iced::theme::palette::Seed {
        background: rgb(0x0b0d10),
        text: rgb(0xe8eaed),
        primary: rgb(0x6f9bff),
        success: rgb(0x5fd38d),
        warning: rgb(0xffb547),
        danger: rgb(0xff8a7a),
    }
}

/// Our own texts, in German where the app is, else English — kept here rather than in
/// upstream's catalogue and locale files, so those merge cleanly.
pub fn say(english: &'static str, german: &'static str) -> &'static str {
    let languages = crate::i18n::loader().current_languages();
    if languages.first().is_some_and(|language| language.language.as_str() == "de") {
        german
    } else {
        english
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_original_projects_links_lead_to_us_or_nowhere() {
        let issues = "https://github.com/HakanSeven12/OpenCADStudio/issues/new?body=x";
        assert_eq!(link(issues).as_deref(), Some(SUPPORT));
        for gone in [
            "https://patreon.com/HakanSeven12",
            "https://github.com/HakanSeven12/OpenCADStudio/releases/latest",
            "https://github.com/HakanSeven12/OpenCADStudio/discussions",
            "https://hakanseven12.github.io/OpenCADStudio/",
            "https://www.reddit.com/r/OpenCADStudio/",
            "https://open-aec.com/",
            "https://www.youtube.com/watch?v=QFDMSRNrZOU",
        ] {
            assert_eq!(link(gone), None, "{gone}");
        }
        for kept in [HELP, SOURCE, "https://example.com/a-link-in-a-drawing"] {
            assert_eq!(link(kept).as_deref(), Some(kept));
        }
    }
}
