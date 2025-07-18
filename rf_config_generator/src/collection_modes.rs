use std::collections::{HashMap, hash_map};

use crate::{
    Message,
    utils::{self, TimeSortedContainer},
};

#[derive(Debug, Clone)]
pub enum CollectionModesMsg {
    Change((String, CollectionMsg)),
    Add,
    Delete(String),
}

#[derive(Debug, Default, Clone, serde::Serialize, serde::Deserialize)]
#[serde(transparent)]
pub struct CollectionModes {
    map: HashMap<String, TimeSortedContainer<CollectionMode>>,
}

#[derive(Debug, Clone, Default, serde::Serialize, serde::Deserialize)]
struct CollectionMode {
    sample_rate: f64,
    duration: f64,
    gain: f64,
}

#[derive(Debug, Clone)]
enum CollectionMsg {
    ChangeName(String),
    ChangeSampleRate(String),
    ChangeDuration(String),
    ChangeGain(String),
}

impl CollectionMode {
    pub fn update(&mut self, msg: CollectionMsg) {
        match msg {
            CollectionMsg::ChangeSampleRate(c) => {
                if let Ok(rate) = c.parse() {
                    self.sample_rate = rate;
                }
            }
            CollectionMsg::ChangeDuration(c) => {
                if let Ok(duration) = c.parse() {
                    self.duration = duration;
                }
            }
            CollectionMsg::ChangeGain(c) => {
                if let Ok(gain) = c.parse() {
                    self.gain = gain;
                }
            }
            _ => (),
        }
    }

    pub fn view(&self) -> iced::widget::Column<'_, CollectionMsg> {
        iced::widget::column![
            iced::widget::row![
                iced::widget::text("sample_rate"),
                iced::widget::text_input("sample_rate", &format!("{}", self.sample_rate))
                .on_input(|c| { CollectionMsg::ChangeSampleRate(c) }),
            ],
            iced::widget::row![
                iced::widget::text("duration"),
                iced::widget::text_input("duration", &format!("{}", self.duration))
                .on_input(|c| { CollectionMsg::ChangeDuration(c) }),
            ],
            iced::widget::row![
                iced::widget::text("gain"),
                iced::widget::text_input("gain", &format!("{}", self.gain))
                .on_input(|c| { CollectionMsg::ChangeGain(c) }),
            ],
        ]
        .into()
    }
}


impl CollectionModes {
    pub fn update(&mut self, msg: CollectionModesMsg) {
        match msg {
            CollectionModesMsg::Change((key, v)) => {
                if let CollectionMsg::ChangeName(val) = v {
                    if let hash_map::Entry::Occupied(entry) = self.map.entry(key.to_string()) {
                        let (_, v) = entry.remove_entry();
                        self.map.insert(val, v);
                    }
                } else {
                    self.map.get_mut(&key).unwrap().val.update(v);
                }
            }

            CollectionModesMsg::Add => {
                let name = utils::rand_name(|v| self.map.contains_key(v));
                self.map.insert(name, TimeSortedContainer::default());
            }

            CollectionModesMsg::Delete(key) => {
                self.map.remove(&key);
            }
        }
    }

    pub fn view(&self) -> iced::Element<'_, Message> {
        let mut sorted: Vec<(&String, &TimeSortedContainer<_>)> = self.map.iter().collect();
        sorted.sort_by(|x, y| x.1.cmp(y.1));

        let top_row = iced::widget::row![
            iced::widget::button("Add Collection Mode").on_press(CollectionModesMsg::Add),
        ]
        .extend(sorted.into_iter().map(|x| {
            iced::widget::row![
                iced::Element::from(
                    iced::widget::button("Delete").on_press(CollectionModesMsg::Delete(x.0.to_string()))
                ),
                iced::Element::from(iced::widget::column![
                    iced::widget::text_input("collection_name", &x.0)
                        .on_input(|c| CollectionMsg::ChangeName(c)),
                        x.1.val.view()
                ])
                .map(|msg| CollectionModesMsg::Change((x.0.to_string(), msg))),
            ]
            .into()
        }));
        iced::Element::from(top_row).map(|msg| Message::CollectionModes(msg))
    }
}
