//! Piclines: the Piclines Editor's own views and commands (see `crate::piclines`): the
//! start page, About, the web plugin notice, and the commands that would open the
//! original project's pages (help, feedback, donations, release notes, the other edition).

use super::{recent_files_panel, start_action_shape, start_primary_style};
use crate::app::{Message, OpenCADStudio, RecentView};
use crate::piclines::{say, NAME, SOURCE, SUPPORT, HELP};
use crate::ui::style::common::muted_style;
use crate::ui::style::form::dialog_button;
use iced::widget::{button, column, container, row, svg, text, Space};
use iced::{Background, Border, Element, Fill, Length, Task, Theme};
use std::collections::HashMap;
use std::path::PathBuf;

/// The start page: our name, the actions, the recent files.
pub(super) fn start_page<'a>(
    recents: &'a [PathBuf],
    thumbs: &'a HashMap<PathBuf, Option<iced::widget::image::Handle>>,
    recent_limit: usize,
    recent_limit_input: &'a str,
    recent_view: RecentView,
) -> Element<'a, Message> {
    let logo = svg(svg::Handle::from_memory(include_bytes!("../../../assets/logo.svg")))
        .width(Length::Fixed(56.0))
        .height(Length::Fixed(56.0));
    let headline = row![logo, text(NAME).size(40).style(start_primary_style)]
        .spacing(16)
        .align_y(iced::Center);

    let action = |label: String, msg: Message| {
        button(text(label).size(14))
            .on_press(msg)
            .padding([10, 22])
            .style(|theme: &Theme, status| {
                let palette = theme.palette();
                let pair = match status {
                    button::Status::Hovered => palette.background.strong,
                    _ => palette.background.weak,
                };
                start_action_shape(button::Style {
                    background: Some(Background::Color(pair.color)),
                    text_color: pair.text,
                    border: Border {
                        color: palette.background.neutral.color,
                        width: 1.0,
                        ..Default::default()
                    },
                    ..Default::default()
                })
            })
    };
    let command = |name: &str| Message::RibbonToolClick {
        tool_id: name.to_string(),
        event: crate::modules::ModuleEvent::Command(name.to_string()),
    };
    let actions = row![
        action(crate::tr!("start", "new-drawing"), Message::TabNew),
        action(crate::tr!("start", "new-from-template"), command("NEW")),
        action(crate::tr!("start", "open-file"), Message::OpenFile),
        action(crate::tr!("action", "options"), Message::OptionsOpen),
        action(crate::tr!("start", "send-feedback"), command("REPORT")),
    ]
    .spacing(12);

    let welcome = column![
        Space::new().height(Length::Fixed(28.0)),
        container(headline).center_x(Fill),
        Space::new().height(Length::Fixed(26.0)),
        container(actions).center_x(Fill),
    ]
    .width(Fill);

    let recent = recent_files_panel(
        recents,
        thumbs,
        recent_limit,
        recent_limit_input,
        recent_view,
        Length::Fixed(320.0),
    );
    container(row![recent, welcome].spacing(16))
        .padding(16)
        .width(Fill)
        .height(Fill)
        .into()
}

fn surface_style(theme: &Theme) -> container::Style {
    container::Style {
        background: Some(Background::Color(theme.palette().background.weakest.color)),
        border: Border {
            color: theme.palette().background.neutral.color,
            width: 1.0,
            radius: 8.0.into(),
        },
        ..Default::default()
    }
}

/// About: our name, the version, and the source the GPL asks us to offer.
pub(super) fn about(sizing: crate::ui::modal::ModalSizing) -> Element<'static, Message> {
    let logo = svg(svg::Handle::from_memory(include_bytes!("../../../assets/logo.svg")))
        .width(Length::Fixed(72.0))
        .height(Length::Fixed(72.0));
    let hero = container(
        row![
            logo,
            column![
                text(NAME).size(28).style(start_primary_style),
                text(say(
                    "Edit DWG and DXF drawings from Piclines",
                    "DWG- und DXF-Zeichnungen aus Piclines bearbeiten",
                ))
                    .size(11)
                    .style(muted_style),
                text(format!("v{}", env!("OCS_FULL_VERSION"))).size(13),
            ]
            .spacing(5),
        ]
        .spacing(18)
        .align_y(iced::Center),
    )
    .padding([14, 16])
    .width(Fill)
    .style(surface_style);

    let licence = container(
        column![
            text(say(
                "Free software under the GNU General Public License v3.0.",
                "Freie Software unter der GNU General Public License v3.0.",
            ))
            .size(13),
            text(say(
                "You may use, study, share and change it under its terms.",
                "Sie dürfen sie nach deren Bedingungen nutzen, untersuchen, weitergeben und ändern.",
            ))
                .size(11)
                .style(muted_style),
        ]
        .spacing(4),
    )
    .padding([10, 12])
    .width(Fill)
    .style(surface_style);

    let buttons = row![
        Space::new().width(Fill),
        dialog_button(say("Source code", "Quellcode"), Message::OpenUrl(SOURCE.to_string()), false),
        dialog_button(crate::t!("Copy Info"), Message::AboutCopyInfo, true),
    ]
    .spacing(8)
    .align_y(iced::Center);

    container(
        column![hero, licence, buttons]
            .spacing(12)
            .padding(16)
            .width(sizing.width)
            .height(sizing.height),
    )
    .width(sizing.width)
    .height(sizing.height)
    .style(|theme: &Theme| container::Style {
        background: Some(Background::Color(theme.palette().background.base.color)),
        ..Default::default()
    })
    .into()
}

/// In place of upstream's web plugin notice, which offers its desktop download.
pub(super) fn plugins(sizing: crate::ui::modal::ModalSizing) -> Element<'static, Message> {
    container(
        column![
            text(say("Plugins", "Plugins")).size(16),
            text(say(
                "The Piclines Editor has no plugins.",
                "Der Piclines Editor hat keine Plugins.",
            ))
            .size(13)
            .style(muted_style),
            row![
                Space::new().width(Fill),
                dialog_button(crate::t!("Close"), Message::CloseModal, true),
            ],
        ]
        .spacing(10)
        .padding(16)
        .width(sizing.width)
        .height(sizing.height),
    )
    .width(sizing.width)
    .height(sizing.height)
    .style(|theme: &Theme| container::Style {
        background: Some(Background::Color(theme.palette().background.base.color)),
        ..Default::default()
    })
    .into()
}

impl OpenCADStudio {
    /// The commands that would open the original project's pages: ours instead, or
    /// nothing. `None` leaves the command to upstream's own dispatch.
    pub(crate) fn piclines_command(&mut self, cmd: &str) -> Option<Task<Message>> {
        let open = |this: &mut Self, url: &str| crate::sys::open_url(url, this.main_window);
        match cmd {
            "HELP" => Some(open(self, HELP)),
            "REPORT" => {
                let body = format!(
                    "\n\n---\n{NAME} v{} ({}), {}\n",
                    env!("OCS_FULL_VERSION"),
                    env!("OCS_GIT_REV"),
                    crate::sys::platform_info(),
                );
                let url = format!(
                    "{SUPPORT}?subject={}&body={}",
                    crate::sys::percent_encode(NAME),
                    crate::sys::percent_encode(&body)
                );
                Some(open(self, &url))
            }
            "DONATE" | "WEBVERSION" | "CHANGELOG" => {
                self.command_line
                    .push_info(&format!("{cmd}: {}", say("not in the Piclines Editor", "nicht im Piclines Editor")));
                Some(Task::none())
            }
            _ => None,
        }
    }
}
