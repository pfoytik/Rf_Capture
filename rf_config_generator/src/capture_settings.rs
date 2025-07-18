use std::{fmt::Display, str::FromStr};

use crate::Message;

#[derive(Debug, Default, Clone, serde::Serialize, serde::Deserialize)]
pub struct CaptureSettings {
    sample_rates: Vec<f64>,
    durations: Vec<f64>,
    gains: Vec<f64>,
    #[serde(skip)]
    compression_options: iced::widget::combo_box::State<CompressionOptions>,
    #[serde(skip)]
    compression_option: Option<CompressionOptions>,
    compression: String,
    compression_level: u64,
}

struct CompressionState {}

#[derive(Debug, Clone)]
pub enum CompressionOptions {
    ZStd,
    Invalid,
}

impl Display for CompressionOptions {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::ZStd => write!(f, "zstd"),
            Self::Invalid => write!(f, "INVALID"),
        }
    }
}

#[derive(Debug, Clone)]
pub enum CaptureSettingsMsg {
    AddSampleRate,
    UpdateSampleRate((String, usize)),
    DelSampleRate(usize),
    AddDuration,
    UpdateDuration((String, usize)),
    DelDuration(usize),
    AddGain,
    UpdateGain((String, usize)),
    DelGain(usize),
    ChangeCompression(String),
    ChangeCompressionLevel(u64),
}

impl From<CaptureSettingsMsg> for Message {
    fn from(value: CaptureSettingsMsg) -> Self {
        Message::CaptureSettingsMsg(value)
    }
}

fn change_if_valid<T: FromStr>(string: String, val: &mut T) {
    if let Ok(parsed) = string.parse() {
        *val = parsed;
    }
}

impl CaptureSettings {
    pub fn update(&mut self, msg: Message) {

        let Message::CaptureSettingsMsg(msg) = msg else {return;};

        match msg {
            CaptureSettingsMsg::AddSampleRate => {
                self.sample_rates.push(0.0);
            }
            CaptureSettingsMsg::UpdateSampleRate((val, id)) => {
                change_if_valid(val, &mut self.sample_rates[id]);
            }
            CaptureSettingsMsg::DelSampleRate(id) => {
                self.sample_rates.remove(id);
            }
            CaptureSettingsMsg::AddDuration => {
                self.durations.push(0.0);
            }
            CaptureSettingsMsg::UpdateDuration((val, id)) => {
                change_if_valid(val, &mut self.durations[id]);
            }
            CaptureSettingsMsg::DelDuration(id) => {
                self.durations.remove(id);
            }
            CaptureSettingsMsg::AddGain => {
                self.gains.push(0.0);
            }
            CaptureSettingsMsg::UpdateGain((val, id)) => {
                change_if_valid(val, &mut self.gains[id]);
            }
            CaptureSettingsMsg::DelGain(id) => {
                self.gains.remove(id);
            }
            CaptureSettingsMsg::ChangeCompression(option) => {
                self.compression = option;
            }
            CaptureSettingsMsg::ChangeCompressionLevel(val) => {
                self.compression_level = val;
            }
        }

    }

    pub fn view(&self) -> iced::Element<Message> {
        iced::widget::row![
            iced::widget::column![
                iced::widget::container(iced::widget::text("Sample Rates")).center(iced::Length::Shrink),
                iced::widget::button("Add")
                    .on_press(Message::from(CaptureSettingsMsg::AddSampleRate)),
            ]
            .extend(
                self.sample_rates
                    .iter()
                    .enumerate()
                    .map(|(i, _)| self.sample_rate_widget(i))
            ),
            iced::widget::column![
                iced::widget::container(iced::widget::text("Durations")).center(iced::Length::Shrink),
                iced::widget::button("Add")
                    .on_press(Message::from(CaptureSettingsMsg::AddDuration)),
            ]
            .extend(
                self.durations
                    .iter()
                    .enumerate()
                    .map(|(i, _)| self.duration_widget(i))
            ),
            iced::widget::column![
                iced::widget::container(iced::widget::text("Gains")).center(iced::Length::Shrink),
                iced::widget::button("Add").on_press(Message::from(CaptureSettingsMsg::AddGain)),
            ]
            .extend(
                self.gains
                    .iter()
                    .enumerate()
                    .map(|(i, _)| self.gains_widget(i))
            ),
            iced::widget::column![
                iced::widget::text_input(
                    "Compression Type",
                    &self.compression
                )
                .on_input(|c| {
                    Message::from(CaptureSettingsMsg::ChangeCompression(c))
                }),
                iced::widget::text_input(
                    "Compression Level",
                    &format!("{}", self.compression_level)
                )
                .on_input(|c| {
                    if let Ok(parsed) = c.parse() {
                        Message::from(CaptureSettingsMsg::ChangeCompressionLevel(parsed))
                    } else {
                        Message::None
                    }
                }),
            ],
        ]
        .spacing(10)
        .into()
    }

    pub fn sample_rate_widget(&self, id: usize) -> iced::Element<Message> {
        iced::widget::row![
            iced::widget::button("Remove")
                .on_press(Message::from(CaptureSettingsMsg::DelSampleRate(id))),
            iced::widget::text_input("0", &format!("{}", self.sample_rates[id]))
                .on_input(move |c| Message::from(CaptureSettingsMsg::UpdateSampleRate((c, id)))),
        ]
        .into()
    }
    pub fn duration_widget(&self, id: usize) -> iced::Element<Message> {
        iced::widget::row![
            iced::widget::button("Remove")
                .on_press(Message::from(CaptureSettingsMsg::DelDuration(id))),
            iced::widget::text_input("0", &format!("{}", self.durations[id]))
                .on_input(move |c| Message::from(CaptureSettingsMsg::UpdateDuration((c, id)))),
        ]
        .into()
    }
    pub fn gains_widget(&self, id: usize) -> iced::Element<Message> {
        iced::widget::row![
            iced::widget::button("Remove").on_press(Message::from(CaptureSettingsMsg::DelGain(id))),
            iced::widget::text_input("0", &format!("{}", self.gains[id]))
                .on_input(move |c| Message::from(CaptureSettingsMsg::UpdateGain((c, id)))),
        ]
        .into()
    }
}
