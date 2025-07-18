use std::{fs::File, io::BufWriter};

use crate::{config::Config, toolbar::ToolbarMsg};

mod capture_settings;
mod collection_modes;
mod config;
mod frequency;
mod scheduling;
mod toolbar;
mod utils;

#[derive(Debug, Clone)]
enum Message {
    None,
    Toolbar(ToolbarMsg),
    Frequency(frequency::FrequencyMessage),
    CaptureSettingsMsg(capture_settings::CaptureSettingsMsg),
    CollectionModes(collection_modes::CollectionModesMsg),
    Scheduling(scheduling::SchedulingMsg),
}

#[derive(Default)]
struct App {
    toolbar: toolbar::Toolbar,
    config: config::Config,
}

impl App {
    fn update(&mut self, message: Message) -> iced::Task<Message> {
        match message {
            Message::Toolbar(mut tb) => {
                match &mut tb {
                    ToolbarMsg::OpenedFile(conf) => {
                        self.config = conf.clone();
                    }
                    ToolbarMsg::SaveFile(_) => {
                        return self
                            .toolbar
                            .update(ToolbarMsg::SaveFile(Some(self.config.clone())));
                    }
                    ToolbarMsg::NewFile => {
                        self.config = Config::default();
                    }
                    _ => (),
                }
                self.toolbar.update(tb)
            }
            Message::None => iced::Task::none(),

            _ => self.config.update(message).into(),
        }
    }

    fn view(&self) -> iced::Element<Message> {
        iced::widget::column![
            iced::widget::container(self.toolbar.view())
                .align_top(iced::Length::Shrink)
                .align_left(iced::Length::Shrink),
            iced::widget::Scrollable::new(self.config.view()),
        ]
        .spacing(30)
        .into()
    }
}

fn main() -> iced::Result {
    iced::run("Hello World!", App::update, App::view)
}
