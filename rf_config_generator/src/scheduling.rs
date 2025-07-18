use crate::Message;


#[derive(Debug, Clone)]
pub enum SchedulingMsg {
   Change(usize, ChangeMsg),
   Add,
   Delete(usize),
}

#[derive(Debug, Clone)]
pub enum ChangeMsg {
    Name(String),
    Start(String),
    End(String),
}

#[derive(Debug, Default, Clone, serde::Serialize, serde::Deserialize)]
pub struct Scheduling {
    time_slots: Vec<TimeSlot>,
}

#[derive(Debug, Default, Clone, serde::Serialize, serde::Deserialize)]
struct TimeSlot {
    name: String,
    start: String,
    end: String,
}



impl TimeSlot {
    pub fn update(&mut self, msg: ChangeMsg) {
        match msg {
            ChangeMsg::Name(c) => self.name = c,
            ChangeMsg::Start(c) => self.start = c,
            ChangeMsg::End(c) => self.end = c,
        }
    }

    pub fn view(&self) -> iced::widget::Column<'_, ChangeMsg> {
        iced::widget::column![
            iced::widget::row![
                iced::widget::text("name"),
                iced::widget::text_input("", &self.name).on_input(|c| ChangeMsg::Name(c)),
            ],
            iced::widget::row![
                iced::widget::text("start"),
                iced::widget::text_input("", &self.start).on_input(|c| ChangeMsg::Start(c)),
            ],
            iced::widget::row![
                iced::widget::text("end"),
                iced::widget::text_input("", &self.end).on_input(|c| ChangeMsg::End(c)),
            ],
        ]
    }
}

impl Scheduling {
    pub fn update(&mut self, msg: SchedulingMsg) {
        match msg {
            SchedulingMsg::Add => {
                self.time_slots.push(TimeSlot::default());
            }
            SchedulingMsg::Change(id, c) => {
                self.time_slots[id].update(c);
            }
            SchedulingMsg::Delete(id) => {
                self.time_slots.remove(id);
            }
        }
    }

    pub fn view(&self) -> iced::Element<'_, Message> {
        
        iced::Element::from(
            iced::widget::row![
                iced::widget::button("Add Schedule").on_press(SchedulingMsg::Add),
            ].extend(self.time_slots.iter().enumerate().map(|(i, t)| {
                iced::widget::column![
                    iced::widget::button("Delete").on_press(SchedulingMsg::Delete(i)),
                    iced::Element::from(t.view()).map(move |c| SchedulingMsg::Change(i, c)),
                ].into()
            })
        )).map(|c| Message::Scheduling(c))
    }
}

