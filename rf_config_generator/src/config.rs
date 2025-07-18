use crate::{capture_settings, collection_modes, frequency, scheduling, Message};


#[derive(Default, Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Config {
    frequencies: frequency::FrequencyConfig,
    capture_settings: capture_settings::CaptureSettings,
    collection_modes: collection_modes::CollectionModes,
    scheduling: scheduling::Scheduling,
}

impl Config {
    pub fn update(&mut self, msg: crate::Message) {

        match msg {
            crate::Message::Frequency(f) => {
                self.frequencies.update(Message::Frequency(f));
            },

            crate::Message::CaptureSettingsMsg(f) => {
                self.capture_settings.update(Message::CaptureSettingsMsg(f));
            },

            crate::Message::CollectionModes(f) => {
                self.collection_modes.update(f);
            }

            crate::Message::Scheduling(f) => {
                self.scheduling.update(f);
            }

            _ => ()
        };
    }

    pub fn view(&self) -> iced::Element<crate::Message> {
        iced::widget::column![
            self.frequencies.view(),
            self.capture_settings.view(),
            self.collection_modes.view(),
            self.scheduling.view(),
        ].spacing(20).into()
    }
}
