use std::collections::{HashMap, hash_map};

use iced::{Pixels, widget::column};
use serde::ser::SerializeStruct;

use crate::Message;

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
struct Frequency {
    pub name: String,
    pub freq: f64,
    #[serde(skip, default="rand::random")]
    id: u64,
    pub description: String,
}

#[derive(Debug, PartialEq, Clone, serde::Serialize, serde::Deserialize)]
#[serde(transparent)]
struct FreqGroup {
    pub vec: Vec<Frequency>,
    #[serde(skip, default="default_instant")]
    time: std::time::Instant,
}

impl From<Vec<Frequency>> for FreqGroup {
    fn from(value: Vec<Frequency>) -> Self {
        Self {
            vec: value,
            time: std::time::Instant::now(),
        }
    }
}

fn default_instant() -> std::time::Instant {
    std::time::Instant::now()
}

impl PartialOrd for FreqGroup {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.time.partial_cmp(&other.time)?)
    }
}

impl Default for FreqGroup {
    fn default() -> Self {
        Self {
            vec: Vec::default(),
            time: std::time::Instant::now(),
        }
    }
}

#[derive(Debug, Default, Clone, serde::Serialize, serde::Deserialize)]
#[serde(transparent)]
pub struct FrequencyConfig {
    frequencies: HashMap<String, FreqGroup>,
}

#[derive(Debug, Clone)]
enum FreqAction {
    NameUpdated((u64, String)),
    FreqUpdated((u64, String)),
    DescUpdated((u64, String)),
}

impl FreqAction {
    pub fn get_id(&self) -> u64 {
        match self {
            Self::NameUpdated((x, _)) => *x,
            Self::FreqUpdated((x, _)) => *x,
            Self::DescUpdated((x, _)) => *x,
        }
    }
}

#[derive(Debug, Clone)]
pub enum FrequencyMessage {
    AddGroup,
    GroupNameUpdated((String, String)),
    AddFreq(String),
    DelGroup(String),
    DelFreq(u64),
    FreqAction(FreqAction),
}

impl From<FreqAction> for FrequencyMessage {
    fn from(value: FreqAction) -> Self {
        FrequencyMessage::FreqAction(value)
    }
}

impl From<FrequencyMessage> for Message {
    fn from(value: FrequencyMessage) -> Self {
        Message::Frequency(value)
    }
}

impl From<FreqAction> for Message {
    fn from(value: FreqAction) -> Self {
        Message::Frequency(value.into())
    }
}

impl Frequency {
    pub fn new(id: u64) -> Self {
        Frequency {
            name: String::new(),
            freq: 0.0,
            id,
            description: String::new(),
        }
    }
    pub fn update(&mut self, msg: FreqAction) {

        if self.id != msg.get_id() { return; }
        match msg {
            FreqAction::NameUpdated((_, name)) => self.name = name,
            FreqAction::DescUpdated((_, desc)) => self.description = desc,
            FreqAction::FreqUpdated((_, freq)) => {
                let Ok(parsed): Result<f64, _> = freq.parse() else {
                    return;
                };
                self.freq = parsed;
            }
        }
    }

    pub fn view(&self) -> iced::Element<Message> {
        let column = iced::widget::column![
            iced::widget::text_input("freq_name", &self.name)
                .on_input(|c| Message::from(FreqAction::NameUpdated((self.id, c)))),
            iced::widget::text_input("frequency_value", &format!("{}", self.freq))
                .on_input(|c| Message::from(FreqAction::FreqUpdated((self.id, c)))),
            iced::widget::text_input("description (human readable)", &self.description)
                .on_input(|c| Message::from(FreqAction::DescUpdated((self.id, c)))),
        ];
        iced::widget::row![
            iced::widget::button("Delete")
                .on_press(Message::from(FrequencyMessage::DelFreq(self.id))),
            column,
        ]
        .into()
    }
}

impl FrequencyConfig {
    pub fn update(&mut self, msg: Message) -> Message {
        if let Message::Frequency(f) = msg {
            match f {
                FrequencyMessage::AddGroup => {
                    let mut rand_byte: u8 = rand::random();
                    let mut rand_name = format!("group_{:x}", rand_byte);
                    while self.frequencies.contains_key(&rand_name) {
                        rand_byte = rand::random();
                        rand_name = format!("group_{:x}", rand_byte);
                    }
                    self.frequencies
                        .insert(rand_name.clone(), Vec::new().into());
                    Message::None
                }

                FrequencyMessage::GroupNameUpdated((key, new_key)) => {
                    if let hash_map::Entry::Occupied(entry) = self.frequencies.entry(key) {
                        let (_, v) = entry.remove_entry();
                        self.frequencies.insert(new_key, v);
                        Message::None
                    } else {
                        Message::None
                    }
                }

                FrequencyMessage::AddFreq(key) => {
                    self.frequencies
                        .get_mut(&key)
                        .unwrap()
                        .vec
                        .push(Frequency::new(rand::random()));
                    Message::None
                }

                FrequencyMessage::DelFreq(id) => {
                    self.frequencies
                        .values_mut()
                        .for_each(|x| {
                            x.vec.retain(|x| x.id != id);
                        });
                    Message::None
                }

                FrequencyMessage::DelGroup(key) => {
                    let _ = self.frequencies.remove(&key);
                    Message::None
                }

                FrequencyMessage::FreqAction(action) => {
                    self.frequencies.values_mut().for_each(|x| x.vec.iter_mut().for_each(|x| x.update(action.clone())));
                    Message::None
                }
            }
        } else {
            Message::None
        }
    }

    pub fn view(&self) -> iced::Element<Message> {
        let mut sorted_map = self.frequencies.iter().collect::<Vec<(&String, &FreqGroup)>>();
        sorted_map.sort_by(|a,b| a.1.partial_cmp(b.1).unwrap());
        iced::widget::row![
            iced::widget::button("Add Frequency Group")
                .on_press(Message::from(FrequencyMessage::AddGroup)),
        ]
        .extend(sorted_map.into_iter().map(|(k, v)| {
            let col = column![
                iced::widget::button("Delete").on_press(Message::from(FrequencyMessage::DelGroup(k.to_string()))),
                iced::widget::text_input("group_name", k).on_input(|c| Message::from(
                    FrequencyMessage::GroupNameUpdated((k.clone(), c))
                )),
                iced::widget::button("Add Frequency")
                    .on_press(Message::from(FrequencyMessage::AddFreq(k.clone())))
            ];
            col.extend(v.vec.iter().map(|x| x.view()))
                .spacing(8)
                .into()
        }))
        .into()
    }
}
