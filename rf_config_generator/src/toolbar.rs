use std::path::PathBuf;

use iced::widget;
use rfd::FileDialog;

use crate::{config::{self, Config}, Message};

pub enum ToolbarErr {
    Serialize(serde_json::Error),
    NoFileSelected,
    FileIoError(std::io::Error),
}

impl std::fmt::Display for ToolbarErr {

    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Serialize(e) => write!(f,"{}", e),
            Self::NoFileSelected => write!(f, "No File Selected"),
            Self::FileIoError(e) => write!(f,"{}", e),
        }
    }
}

#[derive(Debug, Clone)]
pub enum ToolbarMsg {
    OpenFile,
    SaveFile(Option<Config>),
    NewFile,
    // Full deserialized config from opened file
    OpenedFile(Config),
    // Path to file to save to
    SavedFile,
    Error,
}

impl From<ToolbarMsg> for Message {
    fn from(value: ToolbarMsg) -> Self {
        Message::Toolbar(value)
    }
}

#[derive(Default, Debug, Clone, Copy)]
pub struct Toolbar;

impl Toolbar {
    pub fn view(&self) -> widget::Row<Message> {
        widget::row![
            widget::button("Open File...").on_press(Message::from(ToolbarMsg::OpenFile)),
            widget::button("Save To File...").on_press(Message::from(ToolbarMsg::SaveFile(None))),
            widget::button("New Config").on_press(Message::from(ToolbarMsg::NewFile)),
        ]
    }

    pub fn update(&mut self, message: ToolbarMsg) -> iced::Task<Message> {
        match message {
            ToolbarMsg::OpenFile => {
                iced::Task::perform(Self::open_file(), |c| {
                    match c {
                        Some(conf) => ToolbarMsg::OpenedFile(conf),
                        None => ToolbarMsg::Error,
                    }.into()
                })
            }
            ToolbarMsg::SaveFile(conf) => {
                if let Some(conf) = conf {
                    iced::Task::perform(Self::save_file(conf), |res| {
                        if let Err(e) = res {
                            eprintln!("Error saving file! {e}");
                            return Message::from(ToolbarMsg::Error);
                        } else {
                            return Message::from(ToolbarMsg::SavedFile);
                        }
                    })
                } else {
                    iced::Task::none()
                }
            }
            _ => iced::Task::none()
        }
    }

    async fn open_file() -> Option<Config> {
        let f = rfd::AsyncFileDialog::new()
            .add_filter("config", &["json"])
            .pick_file()
            .await?
            .read()
            .await;
        
        match serde_json::from_slice(&f) {
            Ok(conf) => Some(conf),
            Err(e) => {
                eprintln!("Error opening file {e}");
                None
            }
        }
    }

    async fn save_file(conf: Config) -> Result<(), ToolbarErr> {
        let f = rfd::AsyncFileDialog::new()
            .add_filter("config", &["json"])
            .save_file()
            .await;

        let Some(f) = f else { return Err(ToolbarErr::NoFileSelected); };
        let serialized = serde_json::to_string_pretty(&conf);

        let Ok(serialized) = serialized else { return Err(ToolbarErr::Serialize(serialized.unwrap_err())); };

        match f.write(serialized.as_bytes()).await {
            Ok(_) => Ok(()),
            Err(e) => Err(ToolbarErr::FileIoError(e))
        }
    }
}
